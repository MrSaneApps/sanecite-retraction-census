#!/usr/bin/env python3
"""Candidate top-10 lists from the Phase 2 census (headline scope: judged, paperwork retractions left out).
Writes rank.json with the top 30 of each list, so entries that fail the reading check can drop out and the
next one moves up. Lists:
  papers   - retracted papers most often still cited as support after retraction (count), with rate
  journals - citing journals: (a) most citations of retracted work as support (count); (b) highest rate with n >= MIN_J
  authors  - citing authors, identified by ORCID only: most of their papers citing retracted work as support
usage: python3 rank.py <site data/phase2 dir> <stage2_v31.jsonl.gz> [citer_authors.jsonl] > rank.json"""
import csv, gzip, json, sys
from collections import Counter, defaultdict

P2, ST2 = sys.argv[1], sys.argv[2]
AUTH = sys.argv[3] if len(sys.argv) > 3 else None
ADMIN = "administrative (no fault found in the science)"
MIN_J = 100
rows = [r for r in csv.DictReader(open(f"{P2}/citations.csv")) if r["label"] != "unclear" and r["retraction_reason"] != ADMIN]
# Named lists use only citations to papers PubMed links to a retraction notice: no replaced originals, no records
# that are the corrected replacement, no unconfirmed retractions (paper_status_class.json from status_all.py).
STATUS = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else None
if STATUS:
    rows = [r for r in rows if STATUS.get(r["retracted_pmid"]) == "retracted (linked)"]
meta = {}
for line in gzip.open(ST2, "rt"):
    d = json.loads(line)
    meta.setdefault(d["retracted_pmid"], {"title": d.get("retracted_title"), "journal": d.get("retracted_journal"),
                                          "doi": d.get("retracted_doi")})


def wilson_low(k, n, z=1.96):
    if not n: return 0
    p = k / n
    return (p + z * z / (2 * n) - z * ((p * (1 - p) + z * z / (4 * n)) / n) ** .5) / (1 + z * z / n)


out = {"scope": f"{len(rows)} judged citations (paperwork retractions and unclear left out)"}
# papers
by_p = defaultdict(Counter)
for r in rows: by_p[r["retracted_pmid"]][r["label"]] += 1
first = {r["retracted_pmid"]: r for r in rows}
out["papers"] = [{"pmid": p, **meta.get(p, {}), "retraction_year": first[p]["retraction_year"], "reason": first[p]["retraction_reason"],
                  "support": c["substantive"], "judged": sum(c.values()), "flagged": c["aware"],
                  "rate": round(c["substantive"] / sum(c.values()), 4)}
                 for p, c in sorted(by_p.items(), key=lambda x: (-x[1]["substantive"], -sum(x[1].values())))[:30]]
# journals
by_j = defaultdict(Counter); jpapers = defaultdict(set)
for r in rows:
    by_j[r["citing_journal"]][r["label"]] += 1
    if r["label"] == "substantive": jpapers[r["citing_journal"]].add(r["citing_pmcid"])
J = [{"journal": j, "support": c["substantive"], "judged": sum(c.values()), "flagged": c["aware"], "papers_citing_as_support": len(jpapers[j]),
      "rate": round(c["substantive"] / sum(c.values()), 4), "rate_low95": round(wilson_low(c["substantive"], sum(c.values())), 4)}
     for j, c in by_j.items()]
out["journals_by_count"] = sorted(J, key=lambda x: -x["support"])[:30]
out["journals_by_rate"] = sorted([x for x in J if x["judged"] >= MIN_J], key=lambda x: -x["rate"])[:30]
out["journals_min_n"] = MIN_J
out["journals_eligible"] = sum(x["judged"] >= MIN_J for x in J)
# authors (ORCID only)
if AUTH:
    auth = {d["pmcid"]: d for d in map(json.loads, open(AUTH))}
    sup = defaultdict(list)  # citing pmcid -> retracted pmids cited as support
    for r in rows:
        if r["label"] == "substantive": sup[r["citing_pmcid"]].append(r["retracted_pmid"])
    papers_by, retr_by, names = defaultdict(set), defaultdict(set), defaultdict(Counter)
    with_orcid = 0
    for pmc, retr in sup.items():
        a = auth.get(pmc)
        if not a: continue
        ids = {x["orcid"] for x in a["authors"] if x.get("orcid")}
        with_orcid += bool(ids)
        for x in a["authors"]:
            if x.get("orcid"):
                papers_by[x["orcid"]].add(pmc); retr_by[x["orcid"]].update(retr); names[x["orcid"]][x.get("name")] += 1
    out["authors_note"] = (f"{len(sup)} citing papers cite a retracted paper as support; {len(auth)} found in Europe PMC; "
                           f"{with_orcid} have at least one author with an ORCID. Only ORCID-identified authors are ranked.")
    out["authors"] = [{"orcid": o, "name": names[o].most_common(1)[0][0], "papers": sorted(papers_by[o]),
                       "n_papers": len(papers_by[o]), "n_retracted_cited": len(retr_by[o])}
                      for o in sorted(papers_by, key=lambda o: (-len(papers_by[o]), -len(retr_by[o])))[:30]]
print(json.dumps(out, indent=1))
