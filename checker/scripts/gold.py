#!/usr/bin/env python3
"""Build the gold reference from two blind readers of different model families (separate Claude sessions and Muse).

Agreement on the verdict -> gold. Disagreement -> written to an adjudication packet with both verdicts and reasons and
the full item, for a third careful read; adjudicated verdicts are merged back with --adjudicated.
Usage: gold.py SAMPLE.jsonl CLAUDE_GLOB MUSE.jsonl OUT_DIR [--adjudicated FILE.jsonl]"""
import argparse, glob, json, os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("claude_glob"); ap.add_argument("muse"); ap.add_argument("outdir")
    ap.add_argument("--adjudicated", default="")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    rows = {}
    for l in open(a.sample):
        try: x = json.loads(l)
        except json.JSONDecodeError: continue
        if x["status"] == "ok": rows[x["draw"]] = x
    cl = {}
    for f in sorted(glob.glob(a.claude_glob)):
        for l in open(f):
            j = json.loads(l); cl[j["draw"]] = j
    mu = {}
    for l in open(a.muse):
        j = json.loads(l)
        if j.get("parsed"): mu[j["draw"]] = j["parsed"]
    adj = {}
    if a.adjudicated and os.path.exists(a.adjudicated):
        for l in open(a.adjudicated):
            j = json.loads(l); adj[j["draw"]] = j
    gold, disagree = [], []
    for d in sorted(set(cl) & set(mu)):
        c, m = cl[d]["verdict"], mu[d]["verdict"]
        if c == m:
            gold.append({"draw": d, "verdict": c, "citation_type": cl[d].get("citation_type"), "source": "agree"})
        elif d in adj:
            gold.append({"draw": d, "verdict": adj[d]["verdict"], "citation_type": adj[d].get("citation_type"), "source": "adjudicated"})
        else:
            disagree.append(d)
    with open(os.path.join(a.outdir, "gold.jsonl"), "w") as fh:
        for g in gold: fh.write(json.dumps(g) + "\n")
    with open(os.path.join(a.outdir, "adjudicate.md"), "w") as fh:
        for d in disagree:
            r = rows[d]; c = r["context"]; x = r["cited"]
            fh.write(f"## ITEM draw={d}\n\nREADER A said: {cl[d]['verdict']} ({cl[d].get('reason', '')})\n")
            fh.write(f"READER B said: {mu[d]['verdict']} ({mu[d].get('reason', '')}; quote: {mu[d].get('quote', '')[:300]})\n\n")
            fh.write(f"CITING PASSAGE (section: {c.get('section') or 'unknown'}):\n{c.get('before', '')} {c['sentence']} {c.get('after', '')}\n\n")
            fh.write(f"CITED PAPER ({r.get('cited_year') or 'year unknown'}): {x['title']}\n\nABSTRACT:\n{x['abstract']}\n\n")
            for j, p in enumerate(x["passages"]): fh.write(f"[Passage {j + 1}] {p}\n\n")
            fh.write("\n---\n\n")
    n = len(set(cl) & set(mu))
    agree = sum(1 for g in gold if g["source"] == "agree")
    print(json.dumps({"both_read": n, "agree": agree, "agreement": round(agree / n, 3) if n else None,
                      "adjudicated": len(adj), "to_adjudicate": len(disagree), "gold": len(gold)}))


if __name__ == "__main__":
    main()
