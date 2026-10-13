#!/usr/bin/env python3
"""Build the human labelling packet (PROTOCOL.md, Validation): 200 citing papers drawn at random (seed 2027) from the
usable census pairs, excluding every pair already used for development, holdout or confirmation.
Labellers answer the same two questions the models answer, per passage; code turns the answers into labels with the
same rule. Writes <out>/passages.csv, <out>/draw.json.  usage: SANECITE_DATA=... human_packet.py <out_dir> [n]"""
import csv, glob, json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__)); import classify as C
DATA, OUT = os.environ["SANECITE_DATA"], sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 200
used = set()
for fn in glob.glob(f"{DATA}/*gold*.json") + glob.glob(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "*gold*.json")):
    try: used |= {it["pair_id"] for it in json.load(open(fn)).get("items", [])}
    except Exception: pass
recs = []
for l in open(f"{DATA}/stage2_v31.jsonl"):
    try: r = json.loads(l)
    except Exception: continue
    if r["status"] == "ok" and not r.get("is_notice") and r["pair_id"] not in used: recs.append(r)
recs.sort(key=lambda r: r["pair_id"])
draw = random.Random(2027).sample(recs, N)
os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/passages.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["item", "passage", "cited_work_title", "section", "where", "before", "citing_sentence (→ marks the citation)",
                "after", "Q1_disputed (yes/no)", "Q2_use (specific/counted/background/described/unclear)", "notes"])
    for k, r in enumerate(draw, 1):
        for i, c in enumerate(r["contexts"]):
            w.writerow([k, i + 1, r["retracted_title"], c.get("section", ""), c.get("where", "text"),
                        c["before"], c["sentence"], c["after"], "", "", ""])
json.dump({"seed": 2027, "n": N, "excluded_used_pairs": len(used), "pool": len(recs),
           "items": [{"item": k, "pair_id": r["pair_id"], "n_passages": len(r["contexts"])} for k, r in enumerate(draw, 1)]},
          open(f"{OUT}/draw.json", "w"), indent=1)
print(f"drew {N} of {len(recs)} (excluded {len(used)} used pairs); passages: {sum(len(r['contexts']) for r in draw)}")
