#!/usr/bin/env python3
"""Stage 3 judge v3: the v2 prompt, but every model runs with the exact settings its model card lists, and every
reply keeps what is needed for a continuous score.

Why (22 Oct 2026): overnight every reasoning model ran with thinking off and every model was scored by its top
verdict only. The live Cloudflare schemas offer reasoning levels, n (several samples per call), logprobs and JSON
schema output; v2 used none of them. Settings now come from model-cards/configs.json, which the model card gate
(llm_api_research_gate.rb --card) checks against MODEL_CARDS_2026-10-22.md.

Per reply we store the parsed verdict of every sample, P(verdict) from the verdict token's logprobs when the
model returns them, and Clef/Jev probabilities. Scores are computed later (score_v3.py), not here.

Usage: judge_v3.py SAMPLE.jsonl OUT_DIR --config configs.json --models key1,key2 [--draws FILE] [--workers 8]"""
import argparse, json, math, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge_v2 as v2  # noqa: E402  (prompt, parse, typed call, quote check)

llm_bakeoff = v2.llm_bakeoff
VERDICTS = v2.VERDICTS
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["quote", "citation_type", "verdict", "reason"],
          "properties": {"quote": {"type": "string"}, "citation_type": {"type": "string", "enum": list(v2.TYPES)},
                         "verdict": {"type": "string", "enum": list(VERDICTS)}, "reason": {"type": "string"}}}


def parse(content):
    """v2 parse; if only citation_type is off-list (Mistral wrote "cannot_tell" there on draw 2608, 22 Oct), keep the
    verdict, which is all the score uses, and record citation_type as None (amendment 5)."""
    p = v2.parse(content)
    if p or not content:
        return p
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None
    try:
        j = json.loads(m.group(0))
    except json.JSONDecodeError:
        j = v2.loose(m.group(0))
    v = str(j.get("verdict", "")).strip().lower()
    if v not in VERDICTS:
        return None
    return {"verdict": v, "citation_type": None, "quote": str(j.get("quote", ""))[:400], "reason": str(j.get("reason", ""))[:400],
            "lenient_parse": True, "type_off_list": str(j.get("citation_type", ""))[:40]}


def body_extra(cfg):
    """Schema kwargs the harness merges into the request (cf_call extra)."""
    ex = dict(cfg.get("extra") or {})
    if cfg.get("json_schema"):
        if cfg["json_schema"] == "guided_json":  # Mistral Small 3.1 on Workers AI
            ex["guided_json"] = SCHEMA
        else:
            ex["response_format"] = {"type": "json_schema",
                                     "json_schema": {"name": "citation_check", "schema": SCHEMA, "strict": True}}
    return ex


def verdict_logprobs(choice):
    """P(each verdict) from the top_logprobs at the first token of the verdict value, or None."""
    lp = (choice.get("logprobs") or {}).get("content") or []
    if not lp:
        return None
    text, starts = "", []
    for t in lp:
        starts.append(len(text)); text += t.get("token", "")
    m = None
    for m in re.finditer(r'"verdict"\s*:\s*"', text):
        pass
    if not m:
        return None
    pos = m.end()
    idx = next((i for i, s in enumerate(starts) if s <= pos < s + len(lp[i].get("token", "")) or s >= pos), None)
    if idx is None:
        return None
    if starts[idx] < pos:  # token straddles the quote: the value starts inside it
        cut = pos - starts[idx]
        cands = [(c.get("token", "")[cut:], c.get("logprob")) for c in lp[idx].get("top_logprobs") or []]
    else:
        cands = [(c.get("token", ""), c.get("logprob")) for c in lp[idx].get("top_logprobs") or []]
    mass = {v: 0.0 for v in VERDICTS}
    for tok, l in cands:
        tok = tok.strip().lower()
        if not tok or l is None:
            continue
        hits = [v for v in VERDICTS if v.startswith(tok) or tok.startswith(v)]
        if len(hits) == 1:
            mass[hits[0]] += math.exp(l)
    tot = sum(mass.values())
    return {k: v / tot for k, v in mass.items()} if tot > 0 else None  # full precision (amendment 6)


def call_chat(model, cfg, r, token):
    """One request, or cfg["repeats"] requests for models whose schema has no n (gpt-oss, Llama, Mistral)."""
    reps = int(cfg.get("repeats", 1))
    if reps <= 1:
        return _call_chat_once(model, cfg, r, token)
    samples, last, waits = [], {}, 0
    tot = {"pt": 0, "ct": 0, "neurons": 0}
    for _ in range(reps):
        sm, res, w = _call_chat_once(model, cfg, r, token)
        samples += sm or [{"parsed": None, "lp": None, "finish": None}]
        waits += w; last = res
        for u in tot: tot[u] += res.get(u) or 0
    return samples, {**last, **tot}, waits


def _call_chat_once(model, cfg, r, token):
    msgs = [{"role": "system", "content": v2.PROMPTS[cfg.get("prompt", "v2")]}, {"role": "user", "content": v2.user_msg(r)}]
    if cfg.get("no_think_suffix"):
        msgs[1]["content"] += " /no_think"
    prof = {k: cfg[k] for k in ("temperature", "max_tokens", "enable_thinking", "reasoning_effort",
                                "use_max_completion_tokens", "timeout") if k in cfg}
    prof["extra"] = body_extra(cfg)
    res, waits, tries = {}, 0, 0
    while tries < 3:
        res = llm_bakeoff.vendor_call(model, msgs, cf_token=token, profile=prof)
        if v2.REFUSED in str(res.get("error", "")) and waits < 240:  # hourly spend ceiling: wait it out (2 h max)
            waits += 1; time.sleep(30); continue
        if "429" in str(res.get("error", "")) or llm_bakeoff.RATE_WAIT_ERR in str(res.get("error", "")):
            waits += 1; time.sleep(15); continue
        tries += 1
        raw = res.get("raw") or {}
        choices = raw.get("choices") or ([{"message": {"content": res.get("content")}}] if res.get("content") else [])
        samples = []
        for c in choices:
            p = parse(((c.get("message") or {}).get("content")) or "")
            samples.append({"parsed": p, "lp": verdict_logprobs(c), "finish": c.get("finish_reason")})
        if samples and all(s["parsed"] for s in samples):
            return samples, res, waits
        if samples and any(s["parsed"] for s in samples) and tries >= 2:
            return samples, res, waits  # keep partial; bad samples are counted, not hidden
        time.sleep(3 * tries)
    return [], res, waits


def call_typed(model, cfg, r):
    """Clef / Jev. TypeSafe documents a first-option bias and +-0.05 run-to-run wobble, so with "permutations": K the
    verdict options are rotated K ways (one call each) and every call is kept; scoring averages P(major)."""
    k = int(cfg.get("permutations", 1))
    if k <= 1:
        parsed, res, _ = v2.call_typed(model, r, cfg.get("prompt", "v2"))
        return ([{"parsed": parsed, "lp": parsed.get("probabilities") if parsed else None}] if parsed else []), res, 0
    import model_calls as mc
    state = {"citing_passage": v2.citing_text(r), "note": "The arrow \u2192 marks the citation being checked.",
             "cited_paper": v2.excerpt_text(r)}
    opts = list(v2.VERDICT_DEF)
    samples, res, pt = [], {}, 0
    for i in range(k):
        order = opts[i % len(opts):] + opts[: i % len(opts)]
        q = {"verdict": {"type": "choice", "instructions": "Does the cited paper, as shown in the excerpts, support the "
                         "part of the citing sentence that this citation covers?\n" + v2.EXAMPLES,
                         "criteria": {o: v2.VERDICT_DEF[o] for o in order}},
             "citation_type": {"type": "choice", "instructions": "What is the paper cited for?", "criteria": v2.TYPE_DEF}}
        out, err = None, None
        for attempt in range(6):  # 429s back off; no TypeSafe fallback (run_arms.sh unsets the key)
            try:
                out = mc.jev(state, q, model=model); break
            except BaseException as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {str(e)[:200]}"; time.sleep(10 * (attempt + 1))
        ans = (out or {}).get("answers") or {}
        v, t = ans.get("verdict") or {}, ans.get("citation_type") or {}
        if v.get("choice") in VERDICTS and t.get("choice") in v2.TYPES:
            samples.append({"parsed": {"verdict": v["choice"], "citation_type": t["choice"], "quote": "", "reason": "",
                                       "lenient_parse": False}, "lp": v.get("probabilities"), "order": order})
            pt += ((out or {}).get("usage") or {}).get("input_tokens") or 0
        else:
            samples.append({"parsed": None, "lp": None, "order": order, "error": err or json.dumps(out)[:200]})
    res = {"pt": pt, "ct": 0, "error": None if all(s["parsed"] for s in samples) else "typed call failed"}
    return samples, res, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("outdir")
    ap.add_argument("--config", required=True)
    ap.add_argument("--models", required=True, help="config keys")
    ap.add_argument("--draws", default="")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    configs = json.load(open(a.config))
    token = os.environ.get("CF_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN") or ""
    if not token: sys.exit("no CF token in the environment")
    os.makedirs(a.outdir, exist_ok=True)
    rows = [x for x in map(json.loads, open(a.sample)) if x.get("status") == "ok"]
    if a.draws:
        keep = set(json.load(open(a.draws))); rows = [x for x in rows if x["draw"] in keep]
    else:
        sys.exit("--draws is required (a sample file can hold the whole pool: 263 stray Clef calls on 22 Oct)")
    if a.limit: rows = rows[: a.limit]
    keys = a.models.split(",")
    out = {k: os.path.join(a.outdir, k + ".jsonl") for k in keys}
    done = {k: set() for k in keys}
    for k in keys:
        if os.path.exists(out[k]):
            for l in open(out[k]):
                j = json.loads(l)
                if j.get("samples") and all(s.get("parsed") for s in j["samples"]): done[k].add(j["draw"])
    jobs = [(x, k) for x in rows for k in keys if x["draw"] not in done[k]]
    lock, st = threading.Lock(), {"ok": 0, "fail": 0, "t0": time.time()}
    print(f"{time.strftime('%H:%M:%S')} STAGE judge3 start pairs={len(rows)} jobs={len(jobs)} keys={','.join(keys)}", flush=True)

    def work(job):
        x, k = job
        cfg = configs[k]; model = cfg["model"]
        if cfg.get("kind") == "typed":
            samples, res, waits = call_typed(model, cfg, x)
        else:
            samples, res, waits = call_chat(model, cfg, x, token)
        ok = bool(samples) and all(s["parsed"] for s in samples)
        rec = {"draw": x["draw"], "key": k, "model": model, "samples": samples,
               "quote_found": [v2.quote_ok(s["parsed"]["quote"], x) if s["parsed"] else None for s in samples],
               "error": None if ok else str(res.get("error") or (res.get("content") or "")[:300]),
               "usage": {u: res.get(u) for u in ("pt", "ct", "neurons")}, "ms": res.get("ms"), "waits": waits}
        with lock:
            with open(out[k], "a") as fh: fh.write(json.dumps(rec) + "\n")
            st["ok" if ok else "fail"] += 1
            n = st["ok"] + st["fail"]
            if n % 50 == 0 or not ok:
                print(f"{time.strftime('%H:%M:%S')} {'STAGE' if ok else 'FAIL'} judge3 done={n}/{len(jobs)} ok={st['ok']} "
                      f"fail={st['fail']} {'' if ok else k + ' ' + str(rec['error'])[:140]}", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        for _ in ex.map(work, jobs): pass
    print(f"{time.strftime('%H:%M:%S')} DONE judge3 ok={st['ok']} fail={st['fail']} min={(time.time() - st['t0']) / 60:.1f}", flush=True)


if __name__ == "__main__":
    main()
