#!/usr/bin/env python3
"""Step 5: emit per-check feed records + site feed.json + site results.json.

checks.jsonl: one record per RESOLVED work (a check actually happened only
where OpenAlex resolved the DOI). checked_at is taken from the mtime of the
raw batch file that carried the DOI — the real fetch time of this run.
Retraction ISO dates are re-read from the raw RW CSV by Record ID.

feed.json schema:
{generated_at, status:"live", run:{checks_in_run, corpus_total, started_at,
finished_at}, featured:{...#1 verified zombie...}, checks:[newest 200]}

results.json: replaces the site placeholder. status="live" only because every
number written here comes straight out of aggregate.json / top25_verified.json
produced by this run. Denominators are documented in the note field.
"""
import csv, gzip, json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent  # run data under phase1/data, raw pulls under phase1/raw
DATA = BASE / "data"
import os
SITE = Path(os.environ.get("SANECITE_SITE_DIR", BASE / "site_out"))

def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# --- retraction ISO dates by record id, from the raw CSV ---
date_by_record = {}
with open(BASE / "raw" / "retractionwatch_utf8.csv", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        d = (row.get("RetractionDate") or "").strip()
        try:
            dt = datetime.strptime(d, "%m/%d/%Y %H:%M")
            date_by_record[row["Record ID"]] = dt.strftime("%Y-%m-%d")
        except ValueError:
            date_by_record[row["Record ID"]] = None

# --- DOI -> batch fetch time (checked_at) ---
checked_at = {}
for fp in sorted((DATA / "openalex_raw").glob("batch_*.json.gz")):
    ts = fp.stat().st_mtime
    with gzip.open(fp, "rt") as f:
        payload = json.load(f)
    for d in payload["requested_dois"]:
        checked_at[d] = iso(ts)

# --- per-work rows ---
rows = [json.loads(l) for l in open(DATA / "per_work.jsonl")]
agg = json.load(open(DATA / "aggregate.json"))
top25 = json.load(open(DATA / "top25_verified.json"))

checks = []
for r in rows:
    if not r.get("resolved"):
        continue
    cby = {int(y): c for y, c in (r.get("counts_by_year") or {}).items()}
    cited_years = [y for y, c in cby.items() if c > 0]
    reason_short = (r.get("reason") or "").split(";")[0].strip()
    checks.append({
        "checked_at": checked_at.get(r["doi"]),
        "doi": r["doi"],
        "title": r["title"],
        "journal": r["journal"],
        "original_year": r["original_year"],
        "retracted": date_by_record.get(r["record_id"]) or r["retraction_year"],
        "reason": reason_short,
        "post_retraction_citations": r["post_retraction_citations"],
        "latest_citation_year": max(cited_years) if cited_years else None,
        "verdict": "cited-after-retraction" if r["post_retraction_citations"] > 0
                   else "no-post-retraction-citations",
        "sources_agree": r.get("openalex_is_retracted") is True,
    })
# --- downstream extension for the top set (script 07 output, if present) ---
ds_path = DATA / "downstream.json"
if ds_path.exists():
    ds = {d["doi"]: d for d in json.load(open(ds_path))}
    for c in checks:
        if c["doi"] in ds:
            c["downstream_citations"] = ds[c["doi"]]["hop2_citations"]
            c["downstream_reviews"] = ds[c["doi"]]["synthesis_hits"]

checks.sort(key=lambda c: (c["checked_at"] or "", c["doi"]), reverse=True)
with open(BASE / "checks.jsonl", "w") as f:
    for c in checks:
        f.write(json.dumps(c) + "\n")

# --- featured: highest-ranked top-25 entry with NO discrepancy ---
feat_row = next(t for t in top25 if not t["discrepancy"])
feat_work = next(r for r in rows if r["doi"] == feat_row["doi"])
fcby = {int(y): c for y, c in (feat_work.get("counts_by_year") or {}).items()}
fyears = [y for y, c in fcby.items() if c > 0]
featured = {
    "doi": feat_row["doi"],
    "title": feat_row["title"],
    "journal": feat_row["journal"],
    "retracted": feat_row["retraction_year"],
    "post_retraction_citations": feat_row["post_retraction_citations"],
    "latest_citation_year": max(fyears) if fyears else None,
}
if ds_path.exists() and feat_row["doi"] in ds:
    featured["downstream_citations"] = ds[feat_row["doi"]]["hop2_citations"]
    featured["downstream_reviews"] = ds[feat_row["doi"]]["synthesis_hits"]

started_at = "2026-10-13T07:35:19Z"  # pipeline.log START line (census+download)
finished_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
feed = {
    "generated_at": finished_at,
    "status": "live",
    "run": {
        "checks_in_run": len(checks),
        "corpus_total": agg["unique_dois_in_scope"],
        "started_at": started_at,
        "finished_at": finished_at,
    },
    "featured": featured,
    "checks": checks[:200],
}
SITE.mkdir(parents=True, exist_ok=True)
with open(SITE / "feed.json", "w") as f:
    json.dump(feed, f, indent=1)

census = json.load(open(DATA / "census.json"))
note = (f"Retraction Watch via Crossref Labs (pulled 2026-10-13): "
        f"{census['retraction_rows']:,} retraction records. Citation stats cover the "
        f"{agg['unique_dois_in_scope']:,} retracted works with DOIs retracted in 2024 or earlier, "
        f"of which {agg['openalex_resolved']:,} resolved in OpenAlex; post-retraction = citations "
        f"in years after the retraction year (OpenAlex counts_by_year, year granularity). "
        f"Left out as administrative or same-DOI replacements: {agg['excluded_administrative']['papers']:,} papers.")
results = {
    "checks_resolved": agg["openalex_resolved"],
    "cited_after_retraction": agg["cited_at_least_once_post_retraction"],
    "excluded_administrative": agg["excluded_administrative"],
    "note": note,
    "post_retraction_citations": agg["total_post_retraction_citations"],
    "status": "live",
    "still_cited_2025_2026": agg["still_cited_2025_2026"],
    "top_zombie_name": featured["title"],
    "total_retracted": census["retraction_rows"],
    "updated": finished_at,
}
with open(SITE / "results.json", "w") as f:
    json.dump(results, f, indent=1, sort_keys=True)

print(f"checks.jsonl rows: {len(checks)}")
print(f"featured: {featured['doi']} post={featured['post_retraction_citations']}")
print("results.json:", json.dumps(results, indent=1))
