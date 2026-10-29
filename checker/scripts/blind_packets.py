#!/usr/bin/env python3
"""Draw the 100 pairs for the blind second read (seed 7) and write four reading packets without any panel answers."""
import json, os, random

D = os.path.expanduser("work/checker")
rows = []
for l in open(f"{D}/data/sample.jsonl"):
    try: r = json.loads(l)
    except json.JSONDecodeError: continue
    if r["status"] == "ok": rows.append(r)
rows.sort(key=lambda r: r["draw"])
pick = random.Random(7).sample(rows, 100)
os.makedirs(f"{D}/blind", exist_ok=True)
for k in range(4):
    with open(f"{D}/blind/packet-{k + 1}.md", "w") as fh:
        for r in pick[k * 25:(k + 1) * 25]:
            c, d = r["context"], r["cited"]
            fh.write(f"## ITEM draw={r['draw']}\n\nCITING PASSAGE (section: {c.get('section') or 'unknown'}):\n")
            fh.write(f"{c.get('before', '')} {c['sentence']} {c.get('after', '')}\n\n")
            fh.write(f"CITED PAPER ({r.get('cited_year') or 'year unknown'}): {d['title']}\n\nABSTRACT:\n{d['abstract']}\n\n")
            for j, p in enumerate(d["passages"]): fh.write(f"[Passage {j + 1}] {p}\n\n")
            fh.write("\n---\n\n")
json.dump(sorted(r["draw"] for r in pick), open(f"{D}/blind/draws.json", "w"))
print("ok", len(pick))
