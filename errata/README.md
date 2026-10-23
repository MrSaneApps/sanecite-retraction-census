# Errata

The census correction of 20 Oct 2026 (PROTOCOL.md, amendment 11, part 4), as data.

| File | What it is |
|---|---|
| `wrong_records.csv` | Retraction Watch records whose PubMed ID points to a different paper, with the census pairs each one carries (`affected_pair_ids`) |
| `explained_mismatches.csv` | Records whose titles differ for a reason the rule allows (for example, PubMed replaced the record with its own retraction notice) |
| `epmc_titles.jsonl.gz` | Europe PMC title, DOI and year for each of the 12,864 retracted papers with a census pair (pulled 20 Oct 2026) |

`scripts/frame_check.py` rebuilds both CSV files from these titles (`--fetch` pulls any that are missing from the
Europe PMC API). `scripts/analyze_census.py` marks each census row with `wrong_record` and reports the census both as
published and, under `corrected_wrong_records` in `data/census_results.json`, without those pairs.

These files cover the retracted papers that have census pairs. The full scan of all 22,553 frame records found 70
wrong records with 86 later citations; 12 of those citations are census pairs, the ones listed here.
