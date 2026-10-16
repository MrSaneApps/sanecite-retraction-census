#!/usr/bin/env python3
"""Step 1: Retraction Watch census.
Parses raw/retractionwatch_utf8.csv (Crossref Labs distribution, downloaded 2026-10-13).
Outputs:
  - data/census.json : aggregate stats
  - data/works_retracted_le2024.jsonl : nature=Retraction rows with a parseable
    OriginalPaperDOI and retraction year <= 2024 (input to step 2).
All counts are exact from the raw file; nothing is sampled.
"""
import csv, json, re, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent  # run data under phase1/data, raw pulls under phase1/raw
RAW = BASE / "raw" / "retractionwatch_utf8.csv"
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)

def parse_year(s):
    if not s: return None
    s = s.strip()
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y", "%Y-%m-%d", "%Y"):
        try:
            return datetime.strptime(s.split(" ")[0] if fmt == "%Y" else s, fmt).year
        except ValueError:
            continue
    m = re.search(r"(19|20)\d{2}", s)
    return int(m.group(0)) if m else None

def norm_doi(s):
    if not s: return None
    s = s.strip().lower()
    s = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", s).strip()
    return s if s.startswith("10.") else None

total = 0
by_nature = Counter()
by_retraction_year = Counter()          # nature=Retraction only
by_nature_year_all = Counter()
subject_counter = Counter()              # first subject token, nature=Retraction
reason_counter = Counter()               # each ';'-separated reason, nature=Retraction
rows_with_orig_doi = 0
retracted_rows = 0
retracted_with_doi = 0
retracted_le2024_with_doi = 0
retracted_bad_date = 0
works_out = []

with open(RAW, encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f)
    for row in r:
        total += 1
        nature = (row.get("RetractionNature") or "").strip()
        by_nature[nature] += 1
        ry = parse_year(row.get("RetractionDate"))
        if ry: by_nature_year_all[(nature, ry)] += 1
        doi = norm_doi(row.get("OriginalPaperDOI"))
        if doi: rows_with_orig_doi += 1
        if nature != "Retraction":
            continue
        retracted_rows += 1
        if ry is None:
            retracted_bad_date += 1
        else:
            by_retraction_year[ry] += 1
        subj = (row.get("Subject") or "").strip()
        if subj:
            first = subj.split(";")[0].strip()
            subject_counter[first] += 1
        for reason in (row.get("Reason") or "").split(";"):
            reason = reason.strip()
            if reason: reason_counter[reason] += 1
        if doi:
            retracted_with_doi += 1
            if ry is not None and ry <= 2024:
                retracted_le2024_with_doi += 1
                works_out.append({
                    "record_id": row.get("Record ID"),
                    "doi": doi,
                    "title": (row.get("Title") or "").strip(),
                    "journal": (row.get("Journal") or "").strip(),
                    "retraction_year": ry,
                    "original_year": parse_year(row.get("OriginalPaperDate")),
                    "reason": (row.get("Reason") or "").strip(),
                    "subject": subj,
                    "retraction_doi": norm_doi(row.get("RetractionDOI")),
                })

with open(DATA / "works_retracted_le2024.jsonl", "w") as f:
    for w in works_out:
        f.write(json.dumps(w) + "\n")

census = {
    "source_file": str(RAW),
    "source_endpoint": "https://api.labs.crossref.org/data/retractionwatch",
    "total_rows": total,
    "by_nature": dict(by_nature.most_common()),
    "rows_with_original_doi": rows_with_orig_doi,
    "retraction_rows": retracted_rows,
    "retraction_rows_with_doi": retracted_with_doi,
    "retraction_rows_unparseable_date": retracted_bad_date,
    "retraction_rows_doi_and_year_le2024": retracted_le2024_with_doi,
    "retractions_by_year": {str(y): by_retraction_year[y] for y in sorted(by_retraction_year)},
    "top_subjects_first_token": subject_counter.most_common(20),
    "top_reasons": reason_counter.most_common(25),
    "n_subject_tokens_total": len(subject_counter),
}
with open(DATA / "census.json", "w") as f:
    json.dump(census, f, indent=2)

print(json.dumps({k: census[k] for k in ["total_rows","by_nature","rows_with_original_doi",
      "retraction_rows","retraction_rows_with_doi","retraction_rows_doi_and_year_le2024",
      "retraction_rows_unparseable_date"]}, indent=2))
print("retractions_by_year:", census["retractions_by_year"])
print("top_subjects:", subject_counter.most_common(8))
print("top_reasons:", reason_counter.most_common(8))
