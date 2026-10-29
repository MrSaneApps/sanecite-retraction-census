#!/usr/bin/env python3
"""Adjudicate batch-6 disagreements a Claude adjudicator could not complete (PREREG_SYSTEM amendment 5): Gemini 3.8
Flash via OpenRouter, with the same rules text and the same packet text per item. Writes {draw, citation_type,
verdict, reason, adjudicator}.

Usage: adj_openrouter.py RULES.md PACKET.md OUT.jsonl [--model MODEL:free]"""
import argparse, json, os, re, time, urllib.error, urllib.request

V = {"accurate", "minor", "major", "cannot_tell"}
T = {"specific_claim", "background", "method_or_tool", "data_source"}



def free_only(model):
    """Owner 2026-10-23: only free models. A model id without ':free' bills OpenRouter credit, and x-ai/* bills the
    owner's xAI account through BYOK. Paid ids need SANECITE_OR_PAID_OK=1, set by the owner for that run."""
    if not model.endswith(":free") and os.environ.get("SANECITE_OR_PAID_OK") != "1":
        raise SystemExit(f"BLOCKED: {model} is not a ':free' model; it would bill. Use a ':free' id.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rules"); ap.add_argument("packet"); ap.add_argument("out")
    ap.add_argument("--model", default="google/gemma-4-31b-it:free")
    a = ap.parse_args()
    free_only(a.model)
    rules = open(a.rules).read().split("HOW TO WORK")[0].strip()
    system = (rules + "\n\nYou are the adjudicator. Two independent readers disagreed on this item; their verdicts are "
              "shown. Read the item yourself and decide by the rules above; you may agree with either reader or with "
              "neither. Judge only from the text shown.")
    items = [i for i in re.split(r"(?m)^(?=## ITEM )", open(a.packet).read()) if i.startswith("## ITEM")]
    done = {json.loads(l)["draw"] for l in open(a.out)} if os.path.exists(a.out) else set()
    key = os.environ["OPENROUTER_API_KEY"]
    for it in items:
        d = int(re.match(r"## ITEM draw=(\d+)", it).group(1))
        if d in done: continue
        for attempt in range(5):
            try:
                body = {"model": a.model, "messages": [{"role": "system", "content": system},
                        {"role": "user", "content": it}], "response_format": {"type": "json_object"}}
                req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                             headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                r = json.load(urllib.request.urlopen(req, timeout=600))
                txt = r["choices"][0]["message"]["content"] or ""
                v = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
                if v.get("verdict") not in V or v.get("citation_type") not in T: raise ValueError("off-list")
                with open(a.out, "a") as fh:
                    fh.write(json.dumps({"draw": d, "citation_type": v["citation_type"], "verdict": v["verdict"],
                                         "reason": v.get("reason", ""), "adjudicator": r.get("model")}) + "\n")
                print("ok", d, v["verdict"], flush=True); break
            except Exception as e:
                print("retry", d, str(e)[:80], flush=True); time.sleep(10)
        else:
            print("FAIL", d, flush=True)


if __name__ == "__main__":
    main()
