#!/usr/bin/env python3
"""Second reading packets, for list ties found after the first check (2026-10-20 14:30 ET): paper 19918075, tied
on 33 support citations for 9th place (15 drawn at random, as for the other papers), and the citing authors ranked
16-23 (every support citation), who each have 6 papers and could tie on confirmed papers with the 10th-placed authors.
usage: python3 packets2.py <site data/phase2> <stage2_v31.jsonl.gz> <rank.json> <outdir>"""
import json, random, sys
sys.argv = [sys.argv[0]] + sys.argv[1:5]
exec(open(__file__.replace("packets2.py", "packets.py")).read().split("rnd = random.Random")[0])  # shared loading + item()
rnd = random.Random(202610202)
with open(f"{OUT}/packet2_papers.jsonl", "w") as f:
    rs = sorted((r for r in sup if r["retracted_pmid"] == "19918075"), key=lambda r: r["pair_id"])
    for r in rnd.sample(rs, min(15, len(rs))): f.write(json.dumps(item(r, "19918075")) + "\n")
with open(f"{OUT}/packet2_authors.jsonl", "w") as f:
    for a in rank["authors"][15:23]:
        papers = set(a["papers"])
        for r in sorted((r for r in sup if r["citing_pmcid"] in papers), key=lambda r: r["pair_id"]):
            f.write(json.dumps(item(r, a["orcid"] + " " + a["name"])) + "\n")
for k in ("papers", "authors"):
    print(k, sum(1 for _ in open(f"{OUT}/packet2_{k}.jsonl")))
