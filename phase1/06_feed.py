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
produced by this run. Every number in the note is also a field of its own
(pulled_date, openalex_date, total_retracted, dois, matched, checks_resolved,
excluded_administrative), so a reader or a check never has to parse the text.
The dates come from the run itself: SANECITE_RW_PULLED / SANECITE_OA_PULLED if
set; else the Retraction Watch pull date from raw/retractionwatch_utf8.pulled (one
line, YYYY-MM-DD, written when the file is downloaded; a file date changes on any
copy or restore, so it is never used) and the newest OpenAlex batch. Without a
pull date the script stops. The correction note takes its figure and date from
first_count.json, never from text typed here.

Also writes data/last_run.json (when it ran and what it counted), so a job
monitor can tell a missed day from a quiet one.
"""
import csv, gzip, json, re
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent  # run data under phase1/data, raw pulls under phase1/raw
DATA = BASE / "data"
import os
# SANECHECK_SITE_DIR is the name the daily job used before 23 Oct 2026; both work.
SITE = Path(os.environ.get("SANECITE_SITE_DIR") or os.environ.get("SANECHECK_SITE_DIR") or BASE / "site_out")
RW_CSV = BASE / "raw" / "retractionwatch_utf8.csv"
RW_PULLED = BASE / "raw" / "retractionwatch_utf8.pulled"   # the download date, written beside the file
FIRST = json.load(open(BASE / "first_count.json"))         # the first published count and its correction date

def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# --- retraction ISO dates by record id, from the raw CSV ---
date_by_record = {}
with open(RW_CSV, encoding="utf-8-sig", newline="") as f:
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

batch_times = sorted(checked_at.values())
started_at = batch_times[0] if batch_times else None  # first OpenAlex batch of this run
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
pulled_date = os.environ.get("SANECITE_RW_PULLED") or (RW_PULLED.read_text().split()[0] if RW_PULLED.exists() else None)
if not pulled_date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", pulled_date):
    raise SystemExit(f"no Retraction Watch pull date: write it (YYYY-MM-DD) to {RW_PULLED} when the file is downloaded, "
                     f"or set SANECITE_RW_PULLED")
openalex_date = os.environ.get("SANECITE_OA_PULLED") or (batch_times[-1][:10] if batch_times else None)
ex = agg["excluded_administrative"]
dois = agg.get("unique_dois_before_exclusion", agg["unique_dois_in_scope"] + ex.get("papers_incl_unresolved", 0))
matched = agg.get("openalex_resolved_before_exclusion", agg["openalex_resolved"] + ex["papers"])
note = (f"Retraction Watch via Crossref Labs (pulled {pulled_date}): {census['retraction_rows']:,} retraction records; "
        f"{dois:,} DOIs retracted 2024 or earlier; {matched:,} matched in OpenAlex ({openalex_date}). "
        f"Paperwork retractions left out (no fault in the science: out of date, temporary removal, publisher error, "
        f"same-DOI replacement; same rule as the Phase 2 census): {ex['papers']:,} papers, {ex['citations']:,} citations. "
        f"Counted: {agg['openalex_resolved']:,} papers. Post-retraction = citing year strictly after retraction year. "
        f"Correction {FIRST['corrected']}: the first count, {FIRST['post_retraction_citations']:,}, included paperwork retractions.")
results = {
    "pulled_date": pulled_date,
    "openalex_date": openalex_date,
    "dois": dois,
    "matched": matched,
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
with open(DATA / "last_run.json", "w") as f:  # status for a job monitor
    json.dump({"finished_at": finished_at, "started_at": started_at, "pulled_date": pulled_date,
               "openalex_date": openalex_date, "post_retraction_citations": results["post_retraction_citations"],
               "checks_resolved": results["checks_resolved"], "site_dir": str(SITE)}, f, indent=1)

print(f"checks.jsonl rows: {len(checks)}")
print(f"featured: {featured['doi']} post={featured['post_retraction_citations']}")
print("results.json:", json.dumps(results, indent=1))
