#!/usr/bin/env python3
"""Stage 3 judge v2: any Workers AI chat model, or Cloudflare's typed-choice model Clef, on a sample file.

Changes from v1 (judge.py): the prompt asks the model to find and quote the passage the citation relies on first, and
says that support missing from partial excerpts means "cannot_tell", not "major"; four short invented examples; a
design or population overstatement is "minor" when the main point holds. Clef (@cf/cloudflare/clef) gets the same
definitions as typed choices. Calls go through the shared harness (llm_bakeoff.vendor_call) for chat models, and the
census helper (model_calls.jev) for Clef. Resumable per (pair, model).

Usage: judge_v2.py SAMPLE.jsonl OUT_DIR --models m1,m2 [--draws FILE.json] [--workers 8] [--limit N]"""
import argparse, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.expanduser("work/helpers"))
sys.path.insert(0, os.path.expanduser("work/census/protocol/scripts"))
import llm_bakeoff  # noqa: E402

VERDICTS = ("accurate", "minor", "major", "cannot_tell")
TYPES = ("specific_claim", "background", "method_or_tool", "data_source")
REFUSED = "spend guard refused"
TYPED = {"@cf/cloudflare/clef"}
MAX_TOKENS = {"@cf/openai/gpt-oss-120b": 4000, "@cf/openai/gpt-oss-20b": 4000}

VERDICT_DEF = {
    "accurate": "The cited paper's text, as shown, supports the statement as written.",
    "minor": "Broadly supported, but a detail is wrong or overstated: a number, the population, the study design "
             "(for example an observational study described as a trial), or the strength or certainty of the finding. "
             "The main point still holds.",
    "major": "The cited paper does not support the statement: the excerpts show it says something different, "
             "contradicts it, or is about a different topic.",
    "cannot_tell": "The excerpts do not show enough to judge. Use this when the support could be in parts of the paper "
                   "not shown; missing support in partial excerpts is NOT evidence of an error.",
}
TYPE_DEF = {
    "specific_claim": "The sentence states a finding, number or conclusion and credits it to the cited paper.",
    "background": "General context that many papers could support.",
    "method_or_tool": "The paper is cited for a method, protocol, instrument, reagent or software.",
    "data_source": "The paper is cited as the source of data, a cohort or a dataset.",
}
EXAMPLES = """Examples (invented):
- "Drug X cut mortality by 40% [→3]." The cited trial reports a 40% relative reduction in mortality. -> accurate
- "Drug X cut mortality by 60% [→3]." The cited trial reports 40%. -> minor (number wrong, direction right)
- "Randomized trials show X raises risk [→4]." The cited paper is an observational cohort finding higher risk. -> minor
- "X has no effect on Y [→5]." The cited paper reports that X raised Y. -> major (contradicts)
- "Vitamin D prevents fractures [→6]." The cited paper studies vitamin D and mood only. -> major (different topic)
- "X activates the Z pathway [→7]." The excerpts discuss X but none mention Z; the paper may cover it elsewhere. -> cannot_tell"""

SYSTEM = ("You check whether a citation in a scientific paper accurately reports what the cited paper says.\n\n"
          "You get the citing passage, with the citation being checked marked by an arrow (→), and excerpts from the "
          "cited paper: its title, its abstract and the passages most related to the citing passage. Judge only the "
          "part of the citing sentence this citation could support; if the sentence cites several works for different "
          "points, judge the point this paper plausibly covers.\n\n"
          "Work in this order: (1) find the sentence in the excerpts that bears on the claim and copy it exactly; "
          "(2) compare it with the claim; (3) choose the verdict.\n\n"
          "citation_type, one of:\n" + "\n".join(f"- {k}: {v}" for k, v in TYPE_DEF.items()) + "\n\n"
          "verdict, one of:\n" + "\n".join(f"- {k}: {v}" for k, v in VERDICT_DEF.items()) + "\n\n" + EXAMPLES + "\n\n"
          "Answer ONLY with JSON, no other text:\n"
          '{"quote": "the sentence copied exactly from the excerpts, or empty", "citation_type": "...", "verdict": "...", '
          '"reason": "one sentence"}')


CHECKLIST = """Before choosing "accurate", check each of these against the excerpt; any mismatch on a detail the claim relies on is at least "minor":
- population or species (a mouse, cell or animal result cited as if it held in people; adults vs children; a subgroup cited as everyone)
- study design (an observational or cross-sectional study described as a trial, a review cited as a primary study)
- certainty and scope words the paper does not support ("proved", "demonstrated", "consistently", "all", "clearly", "established")
- numbers, units, direction of effect, time period and setting
More examples (invented):
- "In humans, X lowers blood pressure [→8]." The cited study is in rats. -> minor (population)
- "X consistently improves recovery [→9]." The cited single trial found a modest improvement. -> minor (certainty)
- "X is associated with Y [→10]." The cited cohort reports exactly that association. -> accurate"""

SYSTEM_V3 = SYSTEM.replace("Answer ONLY with JSON", CHECKLIST + "\n\nAnswer ONLY with JSON")
PROMPTS = {"v2": SYSTEM, "v3": SYSTEM_V3}


def excerpt_text(r):
    d = r["cited"]
    passages = "\n\n".join(f"[Passage {i + 1}] {p}" for i, p in enumerate(d["passages"]))
    return f"CITED PAPER ({r.get('cited_year') or 'year unknown'}): {d['title']}\n\nABSTRACT:\n{d['abstract']}\n\nMOST RELATED PASSAGES:\n{passages}"


def citing_text(r):
    c = r["context"]
    return f"(section: {c.get('section') or 'unknown'}) {c.get('before', '')} {c['sentence']} {c.get('after', '')}".strip()


def user_msg(r):
    return f"CITING PASSAGE {citing_text(r)}\n\n{excerpt_text(r)}"


def loose(blob):
    j = {}
    for k in ("citation_type", "verdict", "quote", "reason"):
        m = re.search(r'"%s"\s*:\s*(?:"((?:[^"\\]|\\.)*)"|([^\n}]*))' % k, blob)
        if m: j[k] = (m.group(1) if m.group(1) is not None else m.group(2)).strip().rstrip(",")
    return j


def parse(content):
    if not content: return None
    m = re.search(r"\{.*\}", content, re.S)
    if not m: return None
    try: j, lenient = json.loads(m.group(0)), False
    except json.JSONDecodeError: j, lenient = loose(m.group(0)), True
    v, t = str(j.get("verdict", "")).strip().lower(), str(j.get("citation_type", "")).strip().lower()
    if v not in VERDICTS or t not in TYPES: return None
    return {"verdict": v, "citation_type": t, "quote": str(j.get("quote", ""))[:400], "reason": str(j.get("reason", ""))[:400],
            "lenient_parse": lenient}


def norm(s): return re.sub(r"\W+", " ", (s or "").lower()).strip()


def quote_ok(q, r):
    if not q.strip(): return None
    hay = norm(" ".join([r["cited"]["title"], r["cited"]["abstract"]] + r["cited"]["passages"]))
    qn = norm(q)
    return qn in hay or (len(qn) > 40 and qn[: len(qn) // 2] in hay)


def call_chat(m, r, token, prompt="v2"):
    msgs = [{"role": "system", "content": PROMPTS[prompt]}, {"role": "user", "content": user_msg(r)}]
    tries = waits = 0
    res, parsed = {}, None
    while tries < 3:
        kw = {"max_tokens": MAX_TOKENS[m]} if m in MAX_TOKENS else {}
        if "qwen3" in m:  # LLM_VENDOR_API_SOP: Qwen3 on Workers AI has no thinking flag; /no_think in the prompt
            msgs = [msgs[0], {"role": "user", "content": msgs[1]["content"] + " /no_think"}]
        res = llm_bakeoff.vendor_call(m, msgs, cf_token=token, **kw)
        if REFUSED in str(res.get("error", "")) and waits < 40:
            waits += 1; time.sleep(30); continue
        tries += 1
        parsed = parse(res.get("content") or "")
        if parsed: break
        time.sleep(3 * tries)
    return parsed, res, waits


def call_typed(m, r, prompt="v2"):
    import model_calls as mc
    state = {"citing_passage": citing_text(r), "note": "The arrow → marks the citation being checked.",
             "cited_paper": excerpt_text(r)}
    q = {"verdict": {"type": "choice", "instructions": "Does the cited paper, as shown in the excerpts, support the part of "
                     "the citing sentence that this citation covers?\n" + EXAMPLES, "criteria": VERDICT_DEF},
         "citation_type": {"type": "choice", "instructions": "What is the paper cited for?", "criteria": TYPE_DEF}}
    if prompt == "v3": q["verdict"]["instructions"] += "\n" + CHECKLIST
    res, err = None, None
    for attempt in range(3):
        try:
            res = mc.jev(state, q, model=m); break
        except BaseException as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:200]}"; time.sleep(5 * (attempt + 1))
    ans = (res or {}).get("answers") or {}
    v, t = (ans.get("verdict") or {}), (ans.get("citation_type") or {})
    if v.get("choice") not in VERDICTS or t.get("choice") not in TYPES:
        return None, {"error": err or ("no answer: " + json.dumps(res)[:200])}, 0
    u = (res or {}).get("usage") or {}
    return ({"verdict": v["choice"], "citation_type": t["choice"], "quote": "", "reason": "",
             "confidence": v.get("confidence"), "probabilities": v.get("probabilities"), "lenient_parse": False},
            {"pt": u.get("input_tokens"), "ct": u.get("output_tokens")}, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("outdir")
    ap.add_argument("--models", required=True)
    ap.add_argument("--draws", default="")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--prompt", default="v2", choices=sorted(PROMPTS))
    a = ap.parse_args()
    token = os.environ.get("CF_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN") or ""
    if not token: sys.exit("no CF token in the environment")
    os.makedirs(a.outdir, exist_ok=True)
    rows = []
    for l in open(a.sample):
        try: x = json.loads(l)
        except json.JSONDecodeError: continue
        if x["status"] == "ok": rows.append(x)
    if a.draws:
        keep = set(json.load(open(a.draws))); rows = [x for x in rows if x["draw"] in keep]
    if a.limit: rows = rows[: a.limit]
    models = a.models.split(",")
    out = {m: os.path.join(a.outdir, re.sub(r"\W+", "_", m.split("/")[-1]) + ".jsonl") for m in models}
    done = {m: set() for m in models}
    for m in models:
        if os.path.exists(out[m]):
            for l in open(out[m]):
                j = json.loads(l)
                if j.get("parsed"): done[m].add(j["draw"])
    jobs = [(x, m) for x in rows for m in models if x["draw"] not in done[m]]
    lock, st = threading.Lock(), {"ok": 0, "fail": 0, "t0": time.time()}
    print(f"{time.strftime('%H:%M:%S')} STAGE judge2 start pairs={len(rows)} jobs={len(jobs)} models={','.join(m.split('/')[-1] for m in models)}", flush=True)

    def work(job):
        x, m = job
        parsed, res, waits = call_typed(m, x, a.prompt) if m in TYPED else call_chat(m, x, token, a.prompt)
        rec = {"draw": x["draw"], "model": m, "parsed": parsed, "quote_found": quote_ok(parsed["quote"], x) if parsed else None,
               "error": None if parsed else str(res.get("error") or (res.get("content") or "")[:300]),
               "usage": {k: res.get(k) for k in ("pt", "ct", "neurons")}, "ms": res.get("ms"), "guard_waits": waits, "prompt": a.prompt}
        with lock:
            with open(out[m], "a") as fh: fh.write(json.dumps(rec) + "\n")
            st["ok" if parsed else "fail"] += 1
            n = st["ok"] + st["fail"]
            if n % 100 == 0 or not parsed:
                print(f"{time.strftime('%H:%M:%S')} {'STAGE' if parsed else 'FAIL'} judge2 done={n}/{len(jobs)} ok={st['ok']} fail={st['fail']} "
                      f"{'' if parsed else m.split('/')[-1] + ' ' + str(rec['error'])[:140]}", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        for _ in ex.map(work, jobs): pass
    print(f"{time.strftime('%H:%M:%S')} DONE judge2 ok={st['ok']} fail={st['fail']} min={(time.time() - st['t0']) / 60:.1f}", flush=True)


if __name__ == "__main__":
    main()
