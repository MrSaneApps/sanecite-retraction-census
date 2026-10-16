# Phase 1: the count of citations to retracted papers

Counts citations made after retraction for every retracted paper in the Retraction Watch database. No AI model is
involved: this is data work against Crossref and OpenAlex. Phase 2 (the rest of this repository) reads a sample of
those citations to see how they are used.

## Steps (run in order, from this folder)

1. `01_census.py`: reads the Retraction Watch file from Crossref Labs (save it as `raw/retractionwatch_utf8.csv`) and
   keeps retractions with a DOI, retracted in 2024 or earlier.
2. `02_openalex.py`: looks up each DOI in OpenAlex in batches of 50 (`cited_by_count`, `counts_by_year`,
   `is_retracted`). Raw replies are kept in `data/openalex_raw/`.
3. `03_aggregate.py`: a citation counts as post-retraction when the citing year is strictly later than the retraction
   year. Same-year citations are left out because their order is unknowable at year level, so the count is low, not
   high. Papers whose every Retraction Watch record is administrative (`../scripts/groups.py`, the rule Phase 2
   uses) and the 28 same-DOI replacements in `same_doi_replacements.json` are left out and reported as
   `excluded_administrative`.
4. `04_verify_top25.py`: checks the 25 most-cited papers one by one against Crossref.
5. `05_sanity.py`: re-checks 10 random papers against both sources; the counts must match.
6. `06_feed.py`: writes `feed.json` and `results.json` for the website (folder from `SANECITE_SITE_DIR`, default
   `site_out/`). Every number comes from `data/aggregate.json` and `data/top25_verified.json`.
7. `07_downstream.py`: for the top 25, traces papers that cite the citing papers, and finds systematic reviews and
   meta-analyses in that chain. Retraction notices, errata and corrections are counted apart.
8. `08_fallback_diag.py`: records papers whose retraction notice is linked in Crossref only through `updated-by`.

Environment (all optional): `OPENALEX_API_KEY` (OpenAlex allows about 1,000 calls a day without a key; a full run
needs more), `SANECITE_MAILTO` (contact address sent to OpenAlex and Crossref), `SANECITE_SITE_DIR`.

## Published figures

OpenAlex counts change a little every day, so a rerun gives slightly different numbers.

- 16 October 2026 snapshot, current rule (Retraction Watch file of 15 October): 262,998 post-retraction citations;
  32,626 of 51,414 resolved papers cited after retraction (63%); 16,878 still cited in 2025-2026; 1,858 papers and
  23,251 citations left out as administrative or same-DOI replacements. `03_aggregate.py` reproduces each of these
  exactly from that snapshot. The same snapshot under the first rule gives 286,249.
- 13 October 2026, first rule (before the administrative rule was added): 286,050 post-retraction citations;
  33,746 of 53,246 resolved papers cited after retraction; 17,322 still cited in 2025-2026.

A citation-level audit (200 random draws from the 262,998, checked against the citing papers' own reference lists)
found about 96.5% (95% CI 93.7-98.7%) to be real citations. The rest were wrong links in OpenAlex, retraction notices,
a whole-issue record and duplicate records. Taking that into account, about 254,000 are real citations (247,000-260,000).
See https://sanecite.com for the full write-up.
