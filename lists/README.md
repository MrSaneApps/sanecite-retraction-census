# Lists: code and data

The named Lists on sanecite.com (retracted papers, journals and authors whose papers cite retracted work as support),
with the code that builds them. Staged by `scripts/stage_release.py` on 2026-10-29 from the site at 037049d.

| Path | What it is |
|---|---|
| `code/rank.py`, `code/packets*.py`, `code/mkv2.py` | Candidate ranking from the census and the second-reading packets and verdicts |
| `code/lists_data.py`, `code/author_items.py` | Builds `lists.json`, `list_checks.csv`, `retraction_status.csv` and the author items |
| `code/fetch_authors.py`, `code/status_all.py`, `code/crossref_check.py` | Author matching by ORCID iD; retraction status from PubMed and Crossref |
| `code/listfix/` | Corrections of 21 Oct 2026: notices, reason rulings, fields, sync into `lists.json` |
| `code/corrections/` | Corrections of 22 Oct 2026: notice and first-online dates, recounts |
| `code/site/lists.py`, `code/site/charts.py` | The site code that turns the data into the Lists page and its CSV files |
| `readings/` | Second-reading verdicts (one line per citation read, with a one-sentence reason) |
| `data/` | The inputs the page is built from (`lists.json`, `list_corrections.json`, `list_checks.csv`, ...) |
| `csv/` | The CSV files the page offers for download, as published |
| `METHOD.md` | How the Lists are made, step by step |

Code is under the MIT license (`../LICENSE`); SaneCite-made data under CC BY 4.0 (`../LICENSE-DATA`).
`SOURCES.sha256` lists each file's hash before and after staging. Paths to private working folders in the code were
replaced by `work/<name>/`; nothing else was changed. Letters to authors and the replies themselves are not published;
`csv/replies.csv` is the published summary of each reply under the right-of-reply rule.
