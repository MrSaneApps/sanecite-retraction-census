#!/usr/bin/env python3
"""Step 2b: aggregate post-retraction citation stats from OpenAlex pulls.

Method (year granularity): a citation counts as POST-retraction if the citing
year (OpenAlex counts_by_year) is strictly greater than the retraction year
(Retraction Watch RetractionDate year). Same-year citations are excluded
because within-year order is unknowable from these sources.
Duplicates: if several RW records share one OriginalPaperDOI, the EARLIEST
retraction year is used (documented choice; count reported in output).
Scope (amendment 5, 16 Oct 2026; the rule Phase 2 always used): a DOI is left out when EVERY Retraction Watch
record for it is administrative by ../scripts/groups.py (withdrawn as out of date, retract and replace, error by
journal/publisher, temporary removal and similar), or when it is one of the 28 same-DOI replacements or restored
articles in same_doi_replacements.json (the corrected article lives at the same DOI, so later citations point at a
valid article). Left-out papers and their post-retraction citations are reported as excluded_administrative.
Output: data/aggregate.json + data/top50.json (+ per-work table data/per_work.jsonl).
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
import statistics

BASE = Path(__file__).resolve().parent  # run data under phase1/data, raw pulls under phase1/raw
DATA = BASE / "data"

works = [json.loads(l) for l in open(DATA / "works_retracted_le2024.jsonl")]
# dedupe by DOI, earliest retraction year wins
by_doi = {}
dup_records = 0
for w in works:
    d = w["doi"]
    if d in by_doi:
        dup_records += 1
        if w["retraction_year"] < by_doi[d]["retraction_year"]:
            by_doi[d] = w
    else:
        by_doi[d] = w

sys.path.insert(0, str(BASE.parent / "scripts"))
from groups import reason_group, ADMIN_G  # noqa: E402
recs = defaultdict(list)  # every RW record per DOI, not just the earliest
for w in works:
    recs[w["doi"]].append(w)
same_doi = set(json.load(open(BASE / "same_doi_replacements.json"))["dois"])
excluded = {d for d, rs in recs.items() if all(reason_group(r["reason"]) == ADMIN_G for r in rs)} | (same_doi & set(recs))
dois_before_exclusion = len(by_doi)
excluded_rows = {d: by_doi.pop(d) for d in list(by_doi) if d in excluded}

oa = {}
for l in open(DATA / "openalex_works.jsonl"):
    r = json.loads(l)
    d = (r.get("doi") or "").replace("https://doi.org/", "").lower()
    if d: oa[d] = r

rows = []
for d, w in by_doi.items():
    r = oa.get(d)
    if r is None:
        rows.append({**w, "resolved": False})
        continue
    cby = {c["year"]: c["cited_by_count"] for c in r.get("counts_by_year", [])}
    ry = w["retraction_year"]
    post = sum(c for y, c in cby.items() if y > ry)
    latest = sum(c for y, c in cby.items() if y >= 2025)
    rows.append({
        **w, "resolved": True,
        "openalex_id": r.get("id"),
        "openalex_is_retracted": r.get("is_retracted"),
        "openalex_pub_year": r.get("publication_year"),
        "total_cited_by": r.get("cited_by_count"),
        "post_retraction_citations": post,
        "citations_2025_2026": latest,
        "counts_by_year": cby,
    })

ex_post, ex_resolved = 0, 0  # same denominator as the headline: papers resolved in OpenAlex
for d, w in excluded_rows.items():
    r = oa.get(d)
    if r is not None:
        ex_resolved += 1
        ex_post += sum(c["cited_by_count"] for c in r.get("counts_by_year", []) if c["year"] > w["retraction_year"])

with open(DATA / "per_work.jsonl", "w") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")

res = [r for r in rows if r["resolved"]]
posts = sorted(r["post_retraction_citations"] for r in res)
n = len(res)
total_post = sum(posts)
cited_post = sum(1 for p in posts if p > 0)
still_2526 = sum(1 for r in res if r["citations_2025_2026"] > 0)
oa_flag_true = sum(1 for r in res if r["openalex_is_retracted"] is True)
oa_flag_false = sum(1 for r in res if r["openalex_is_retracted"] is False)

def pct(a, b): return round(100.0 * a / b, 2) if b else None

buckets = Counter()
for p in posts:
    if p == 0: buckets["0"] += 1
    elif p == 1: buckets["1"] += 1
    elif p <= 5: buckets["2-5"] += 1
    elif p <= 10: buckets["6-10"] += 1
    elif p <= 50: buckets["11-50"] += 1
    elif p <= 100: buckets["51-100"] += 1
    else: buckets["101+"] += 1

top50 = sorted(res, key=lambda r: -r["post_retraction_citations"])[:50]
top50_out = [{
    "doi": r["doi"], "title": r["title"], "journal": r["journal"],
    "original_year": r["original_year"], "retraction_year": r["retraction_year"],
    "reason": r["reason"], "post_retraction_citations": r["post_retraction_citations"],
    "citations_2025_2026": r["citations_2025_2026"],
    "total_cited_by_openalex": r["total_cited_by"],
    "openalex_is_retracted": r["openalex_is_retracted"],
} for r in top50]
with open(DATA / "top50.json", "w") as f:
    json.dump(top50_out, f, indent=2)

agg = {
    "rw_rows_in_scope": len(works),
    "unique_dois_in_scope": len(by_doi),
    "excluded_administrative": {"papers": ex_resolved, "citations": ex_post, "papers_incl_unresolved": len(excluded_rows),
                                "dois_all_records": len(excluded_rows)},
    "unique_dois_before_exclusion": dois_before_exclusion,      # "DOIs retracted 2024 or earlier" in results.json
    "openalex_resolved_before_exclusion": n + ex_resolved,      # "matched in OpenAlex" in results.json
    "duplicate_rw_records_collapsed": dup_records,
    "openalex_resolved": n,
    "openalex_coverage_pct": pct(n, len(by_doi)),
    "openalex_is_retracted_true": oa_flag_true,
    "openalex_is_retracted_false": oa_flag_false,
    "total_post_retraction_citations": total_post,
    "cited_at_least_once_post_retraction": cited_post,
    "pct_cited_at_least_once_post": pct(cited_post, n),
    "still_cited_2025_2026": still_2526,
    "pct_still_cited_2025_2026": pct(still_2526, n),
    "mean_post": round(statistics.mean(posts), 2) if posts else None,
    "median_post": statistics.median(posts) if posts else None,
    "p90_post": posts[int(0.90 * (n - 1))] if n else None,
    "p99_post": posts[int(0.99 * (n - 1))] if n else None,
    "max_post": posts[-1] if posts else None,
    "distribution": {k: buckets[k] for k in ["0", "1", "2-5", "6-10", "11-50", "51-100", "101+"]},
}
with open(DATA / "aggregate.json", "w") as f:
    json.dump(agg, f, indent=2)
print(json.dumps(agg, indent=2))
