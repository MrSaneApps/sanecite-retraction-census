#!/usr/bin/env python3
"""Reference reader through OpenRouter (PREREG_SYSTEM amendment 4): same v2 rules and user message as judge_v2.py,
one call per citation, written as {draw, citation_type, verdict, reason, quote, model, cost}.

Usage: openrouter_read.py SAMPLE.jsonl DRAWS.json OUT.jsonl [--model MODEL:free] [--gap 2]
Needs OPENROUTER_API_KEY. Resumable: draws already in OUT are skipped."""
import argparse, json, os, re, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge_v2

V = {"accurate", "minor", "major", "cannot_tell"}
T = {"specific_claim", "background", "method_or_tool", "data_source"}



def free_only(model):
    """Owner 2026-10-23: only free models. A model id without ':free' bills OpenRouter credit, and x-ai/* bills the
    owner's xAI account through BYOK. Paid ids need SANECITE_OR_PAID_OK=1, set by the owner for that run."""
    if not model.endswith(":free") and os.environ.get("SANECITE_OR_PAID_OK") != "1":
        raise SystemExit(f"BLOCKED: {model} is not a ':free' model; it would bill. Use a ':free' id.")

def call(model, key, row):
    body = {"model": model, "messages": [{"role": "system", "content": judge_v2.SYSTEM},
                                         {"role": "user", "content": judge_v2.user_msg(row)}],
            "response_format": {"type": "json_object"}, "usage": {"include": True}}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=600))
    if "error" in d: raise RuntimeError(str(d["error"])[:200])
    text = d["choices"][0]["message"]["content"] or ""
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text), d.get("model"), (d.get("usage") or {}).get("cost")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("draws"); ap.add_argument("out")
    ap.add_argument("--model", default="google/gemma-4-31b-it:free"); ap.add_argument("--gap", type=float, default=2)
    a = ap.parse_args()
    free_only(a.model)
    key = os.environ["OPENROUTER_API_KEY"]
    want = set(json.load(open(a.draws)))
    rows = {}
    for l in open(a.sample):
        try: r = json.loads(l)
        except json.JSONDecodeError: continue
        if r.get("status") == "ok" and r["draw"] in want: rows[r["draw"]] = r
    done = {json.loads(l)["draw"] for l in open(a.out) if l.strip()} if os.path.exists(a.out) else set()
    todo = [d for d in sorted(rows) if d not in done]
    print(f"{time.strftime('%H:%M:%S')} STAGE openrouter start todo={len(todo)} done={len(done)} model={a.model}", flush=True)
    ok = fail = 0; spent = 0.0
    for i, d in enumerate(todo):
        for attempt in range(5):
            try:
                v, mv, cost = call(a.model, key, rows[d])
                if v.get("verdict") not in V or v.get("citation_type") not in T:
                    raise ValueError(f"off-list fields {v.get('verdict')}/{v.get('citation_type')}")
                spent += cost or 0
                with open(a.out, "a") as fh:
                    fh.write(json.dumps({"draw": d, "citation_type": v["citation_type"], "verdict": v["verdict"],
                                         "reason": v.get("reason", ""), "quote": v.get("quote", ""), "model": mv,
                                         "cost": cost}) + "\n")
                ok += 1; break
            except urllib.error.HTTPError as e:
                print(f"{time.strftime('%H:%M:%S')} retry draw={d} http={e.code}", flush=True); time.sleep(30 if e.code == 429 else 10)
            except Exception as e:
                print(f"{time.strftime('%H:%M:%S')} retry draw={d} err={str(e)[:100]}", flush=True); time.sleep(10)
        else:
            fail += 1; print(f"{time.strftime('%H:%M:%S')} FAIL draw={d}", flush=True)
        if (i + 1) % 10 == 0:
            print(f"{time.strftime('%H:%M:%S')} STAGE openrouter done={i + 1}/{len(todo)} ok={ok} fail={fail} usd={spent:.2f}", flush=True)
        if spent > 6: print("STOP spend cap $6 reached", flush=True); break
        time.sleep(a.gap)
    print(f"{time.strftime('%H:%M:%S')} DONE openrouter ok={ok} fail={fail} usd={spent:.2f}", flush=True)


if __name__ == "__main__":
    main()
