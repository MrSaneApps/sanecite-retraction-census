#!/usr/bin/env python3
"""Draw the 100 pairs for the blind second read (seed 7) and write four reading packets without any panel answers."""
import json, os, random

import sys
D = os.path.expanduser("work/checker")
SAMPLE, OUTDIR, N, SEED, PER = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
rows = []
for l in open(SAMPLE):
    try: r = json.loads(l)
    except json.JSONDecodeError: continue
    if r["status"] == "ok": rows.append(r)
rows.sort(key=lambda r: r["draw"])
pick = random.Random(SEED).sample(rows, N)
os.makedirs(OUTDIR, exist_ok=True)
for k in range((N + PER - 1) // PER):
    with open(f"{OUTDIR}/packet-{k + 1}.md", "w") as fh:
        for r in pick[k * PER:(k + 1) * PER]:
            c, d = r["context"], r["cited"]
            fh.write(f"## ITEM draw={r['draw']}\n\nCITING PASSAGE (section: {c.get('section') or 'unknown'}):\n")
            fh.write(f"{c.get('before', '')} {c['sentence']} {c.get('after', '')}\n\n")
            fh.write(f"CITED PAPER ({r.get('cited_year') or 'year unknown'}): {d['title']}\n\nABSTRACT:\n{d['abstract']}\n\n")
            for j, p in enumerate(d["passages"]): fh.write(f"[Passage {j + 1}] {p}\n\n")
            fh.write("\n---\n\n")
json.dump(sorted(r["draw"] for r in pick), open(f"{OUTDIR}/draws.json", "w"))
print("ok", len(pick))
