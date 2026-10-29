#!/usr/bin/env python3
"""Reading packets for checking named list entries. One JSONL per list; each line is one citation the census labelled
"cited it as support", with the passage(s) around it. Authors: every such citation. Papers: 15 per paper, journals:
10 per journal, drawn at random with a fixed seed.
usage: python3 packets.py <site data/phase2> <stage2_v31.jsonl.gz> <rank.json> <outdir>"""
import csv, gzip, json, random, sys
from collections import defaultdict

P2, ST2, RANK, OUT = sys.argv[1:5]
csv.field_size_limit(10 ** 9)
rank = json.load(open(RANK))
cit = {r["pair_id"]: r for r in csv.DictReader(open(f"{P2}/citations.csv"))}
ctx = defaultdict(list)
for f in ("contexts-1.csv", "contexts-2.csv"):
    for r in csv.DictReader(open(f"{P2}/{f}")):
        ctx[r["pair_id"]].append({"section": r["section"], "label": r["label"], "before": r["before"], "sentence": r["sentence"], "after": r["after"]})
meta = {}
for line in gzip.open(ST2, "rt"):
    d = json.loads(line)
    meta.setdefault(d["retracted_pmid"], {"retracted_title": d.get("retracted_title"), "retracted_journal": d.get("retracted_journal")})
status = json.load(open(f"{OUT}/paper_status_class.json"))
sup = [r for r in cit.values() if r["label"] == "substantive" and status.get(r["retracted_pmid"]) == "retracted (linked)"
       and r["retraction_reason"] != "administrative (no fault found in the science)"]


def item(r, group):
    return {"group": group, "pair_id": r["pair_id"], "retracted_pmid": r["retracted_pmid"], **meta.get(r["retracted_pmid"], {}),
            "retraction_year": r["retraction_year"], "citing_pmcid": r["citing_pmcid"], "citing_year": r["citing_year"],
            "citing_journal": r["citing_journal"], "census_label": r["label"], "passages": ctx.get(r["pair_id"], [])}


rnd = random.Random(20261020)
with open(f"{OUT}/packet_papers.jsonl", "w") as f:
    for p in rank["papers"][:15]:
        rs = sorted((r for r in sup if r["retracted_pmid"] == p["pmid"]), key=lambda r: r["pair_id"])
        for r in rnd.sample(rs, min(15, len(rs))): f.write(json.dumps(item(r, p["pmid"])) + "\n")
journals = list(dict.fromkeys([j["journal"] for j in rank["journals_by_rate"][:15]] + [j["journal"] for j in rank["journals_by_count"][:15]]))
with open(f"{OUT}/packet_journals.jsonl", "w") as f:
    for j in journals:
        rs = sorted((r for r in sup if r["citing_journal"] == j), key=lambda r: r["pair_id"])
        for r in rnd.sample(rs, min(10, len(rs))): f.write(json.dumps(item(r, j)) + "\n")
with open(f"{OUT}/packet_authors.jsonl", "w") as f:
    for a in rank["authors"][:15]:
        papers = set(a["papers"])
        for r in sorted((r for r in sup if r["citing_pmcid"] in papers), key=lambda r: r["pair_id"]):
            f.write(json.dumps(item(r, a["orcid"] + " " + a["name"])) + "\n")
for k in ("papers", "journals", "authors"):
    print(k, sum(1 for _ in open(f"{OUT}/packet_{k}.jsonl")))
