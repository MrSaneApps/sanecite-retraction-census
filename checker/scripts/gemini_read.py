#!/usr/bin/env python3
"""Reference reader on Gemini (PREREG_SYSTEM amendment 3): same v2 rules and user message as judge_v2.py, one call
per citation, written as {draw, citation_type, verdict, reason, quote, model}. Free-tier pacing with backoff on 429.

Usage: gemini_read.py SAMPLE.jsonl DRAWS.json OUT.jsonl [--model gemini-3.8-flash] [--gap 6]
Needs GEMINI_API_KEY. Resumable: draws already in OUT are skipped."""
import argparse, json, os, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge_v2

V = {"accurate", "minor", "major", "cannot_tell"}
T = {"specific_claim", "background", "method_or_tool", "data_source"}


def call(model, key, row):
    body = {"systemInstruction": {"parts": [{"text": judge_v2.SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": judge_v2.user_msg(row)}]}],
            "generationConfig": {"responseMimeType": "application/json"}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=300))
    text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought"))
    return json.loads(text), d.get("modelVersion")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("draws"); ap.add_argument("out")
    ap.add_argument("--model", default="gemini-3.8-flash"); ap.add_argument("--gap", type=float, default=6)
    a = ap.parse_args()
    key = os.environ["GEMINI_API_KEY"]
    want = set(json.load(open(a.draws)))
    rows = {}
    for l in open(a.sample):
        try: r = json.loads(l)
        except json.JSONDecodeError: continue
        if r.get("status") == "ok" and r["draw"] in want: rows[r["draw"]] = r
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(l)["draw"] for l in open(a.out) if l.strip()}
    todo = [d for d in sorted(rows) if d not in done]
    print(f"{time.strftime('%H:%M:%S')} STAGE gemini start todo={len(todo)} done={len(done)} model={a.model}", flush=True)
    ok = fail = 0
    for i, d in enumerate(todo):
        for attempt in range(6):
            try:
                v, mv = call(a.model, key, rows[d])
                if v.get("verdict") not in V or v.get("citation_type") not in T:
                    raise ValueError(f"off-list fields {v.get('verdict')}/{v.get('citation_type')}")
                with open(a.out, "a") as fh:
                    fh.write(json.dumps({"draw": d, "citation_type": v["citation_type"], "verdict": v["verdict"],
                                         "reason": v.get("reason", ""), "quote": v.get("quote", ""), "model": mv}) + "\n")
                ok += 1; break
            except urllib.error.HTTPError as e:
                wait = 60 if e.code == 429 else 20
                print(f"{time.strftime('%H:%M:%S')} retry draw={d} http={e.code} wait={wait}", flush=True); time.sleep(wait)
            except Exception as e:
                print(f"{time.strftime('%H:%M:%S')} retry draw={d} err={str(e)[:80]}", flush=True); time.sleep(10)
        else:
            fail += 1; print(f"{time.strftime('%H:%M:%S')} FAIL draw={d}", flush=True)
        if (i + 1) % 10 == 0:
            print(f"{time.strftime('%H:%M:%S')} STAGE gemini done={i + 1}/{len(todo)} ok={ok} fail={fail}", flush=True)
        time.sleep(a.gap)
    print(f"{time.strftime('%H:%M:%S')} DONE gemini ok={ok} fail={fail}", flush=True)


if __name__ == "__main__":
    main()
