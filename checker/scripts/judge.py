#!/usr/bin/env python3
"""Stage 3 pilot judge: ask each panel model whether a citation accurately reports what the cited paper says.

Calls go through the shared Workers AI harness (clients/translations/scripts/llm_bakeoff.vendor_call: researched
model settings, the per-model rate limiter and the spend guard). Resumable: a (pair, model) already answered is skipped.

Usage: judge.py SAMPLE.jsonl OUT_DIR [--models m1,m2,m3] [--workers 8] [--limit N]"""
import argparse, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.expanduser("work/helpers"))
import llm_bakeoff  # noqa: E402

PANEL = ["@cf/openai/gpt-oss-120b", "@cf/google/gemma-4-26b-a4b-it", "@cf/nvidia/nemotron-3-120b-a12b"]
# Output caps (deviation 1, 20:50 ET): the harness defaults (12,000 / 2,500 / 8,000) made the spend guard's
# worst-case reservations hit the hourly ceiling at $0.09 of real spend. Real answers are about 120-1,500 tokens.
MAX_TOKENS = {"@cf/openai/gpt-oss-120b": 4000, "@cf/google/gemma-4-26b-a4b-it": 1500, "@cf/nvidia/nemotron-3-120b-a12b": 1500}
REFUSED = "spend guard refused"
VERDICTS = ("accurate", "minor", "major", "cannot_tell")
TYPES = ("specific_claim", "background", "method_or_tool", "data_source")

SYSTEM = """You check whether a citation in a scientific paper accurately reports what the cited paper says.

You get the citing passage, with the citation being checked marked by an arrow (→), and excerpts from the cited
paper: its title, its abstract and the passages most related to the citing sentence. Judge only the part of the
citing sentence that this citation could support. If the sentence cites several works for different points, judge
whether this cited paper supports the point it plausibly covers.

citation_type, one of:
- specific_claim: the sentence states a finding, number or conclusion and credits it to the cited paper
- background: general context that many papers could support
- method_or_tool: the paper is cited for a method, protocol, instrument, reagent or software
- data_source: the paper is cited as the source of data, a cohort or a dataset

verdict, one of:
- accurate: the cited paper supports the statement as written
- minor: broadly supported, but a detail is wrong or overstated (a number, the population, the study design,
  the strength or certainty of the finding), and the main point still holds
- major: the cited paper does not support the statement, contradicts it, or is about something else
- cannot_tell: the excerpts do not contain enough to judge (do not guess "accurate" when the support is not shown)

Answer ONLY with JSON, no other text:
{"citation_type": "...", "verdict": "...", "quote": "up to 40 words copied exactly from the excerpts that support or contradict the statement, or empty", "reason": "one sentence"}"""


def user_msg(r):
    c, d = r["context"], r["cited"]
    passages = "\n\n".join(f"[Passage {i + 1}] {p}" for i, p in enumerate(d["passages"]))
    return (f"CITING PASSAGE (section: {c.get('section') or 'unknown'}):\n{c.get('before', '')} {c['sentence']} {c.get('after', '')}\n\n"
            f"CITED PAPER ({r.get('cited_year') or 'year unknown'}): {d['title']}\n\nABSTRACT:\n{d['abstract']}\n\n"
            f"MOST RELATED PASSAGES FROM THE CITED PAPER:\n{passages}")


def loose(blob):
    """Nemotron sometimes leaves a value unquoted ("reason": The study ...). Read the four fields one by one."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("outdir")
    ap.add_argument("--models", default=",".join(PANEL))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    token = os.environ.get("CF_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN") or ""
    if not token: sys.exit("no CF token in the environment")
    os.makedirs(a.outdir, exist_ok=True)
    rows = []
    for l in open(a.sample):  # the sampler may be mid-write on the last line
        try: rows.append(json.loads(l))
        except json.JSONDecodeError: pass
    rows = [r for r in rows if r["status"] == "ok"]
    if a.limit: rows = rows[: a.limit]
    models = a.models.split(",")
    out = {m: os.path.join(a.outdir, re.sub(r"\W+", "_", m.split("/")[-1]) + ".jsonl") for m in models}
    done = {m: set() for m in models}
    for m in models:
        if os.path.exists(out[m]):
            for l in open(out[m]):
                j = json.loads(l)
                if j.get("parsed"): done[m].add(j["draw"])
    jobs = [(r, m) for r in rows for m in models if r["draw"] not in done[m]]
    lock, stats = threading.Lock(), {"ok": 0, "fail": 0, "t0": time.time()}
    print(f"{time.strftime('%H:%M:%S')} STAGE judge start pairs={len(rows)} jobs={len(jobs)} models={len(models)}", flush=True)

    def work(job):
        r, m = job
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg(r)}]
        parsed, res = None, {}
        tries, waits = 0, 0
        while tries < 3:
            res = llm_bakeoff.vendor_call(m, msgs, cf_token=token, max_tokens=MAX_TOKENS.get(m))
            if REFUSED in str(res.get("error", "")) and waits < 40:  # the spend guard is pacing us: wait, not a failure
                waits += 1; time.sleep(30); continue
            tries += 1
            parsed = parse(res.get("content") or res.get("text") or "")
            if parsed: break
            time.sleep(3 * tries)
        rec = {"draw": r["draw"], "model": m, "parsed": parsed, "quote_found": quote_ok(parsed["quote"], r) if parsed else None,
               "error": None if parsed else str(res.get("error") or (res.get("content") or "")[:300]),
               "usage": {k: res.get(k) for k in ("pt", "ct", "neurons")}, "ms": res.get("ms"), "guard_waits": waits}
        with lock:
            with open(out[m], "a") as fh: fh.write(json.dumps(rec) + "\n")
            stats["ok" if parsed else "fail"] += 1
            n = stats["ok"] + stats["fail"]
            if n % 50 == 0 or not parsed:
                tag = "STAGE" if parsed else "FAIL"
                print(f"{time.strftime('%H:%M:%S')} {tag} judge done={n}/{len(jobs)} ok={stats['ok']} fail={stats['fail']} "
                      f"{'' if parsed else m + ' ' + str(rec['error'])[:160]}", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        for _ in ex.map(work, jobs): pass
    print(f"{time.strftime('%H:%M:%S')} DONE judge ok={stats['ok']} fail={stats['fail']} "
          f"min={(time.time() - stats['t0']) / 60:.1f}", flush=True)


if __name__ == "__main__":
    main()
