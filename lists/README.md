# Lists: code and data

The named Lists on sanecite.com (retracted papers, journals and authors whose papers cite retracted work as support),
with the code that builds them. Staged by `scripts/stage_release.py` on 2026-11-04 from the site at cc7e09e.

| Path | What it is |
|---|---|
| `code/rank.py`, `code/packets*.py`, `code/mkv2.py` | Candidate ranking from the census and the second-reading packets and verdicts |
| `code/lists_data.py`, `code/author_items.py` | Builds `lists.json`, `list_checks.csv`, `retraction_status.csv` and the author items |
| `code/fetch_authors.py`, `code/status_all.py`, `code/crossref_check.py` | Author matching by ORCID iD; retraction status from PubMed and Crossref |
| `code/listfix/` | Corrections of 21 Oct 2026: notices, reason rulings, fields, sync into `lists.json` |
| `code/corrections/` | Corrections of 22 Oct 2026: notice and first-online dates, recounts |
| `code/site/` | The site code that turns the data into the Lists page, its CSV files and the charts (`lists.py`, `charts.py`, `render_charts.mjs`, `charts.js`, the page template and its stylesheet) |
| `readings/` | Second-reading verdicts (one line per citation read, with a one-sentence reason) |
| `data/` | The inputs the page is built from (`lists.json`, `list_corrections.json`, `list_checks.csv`, ...) |
| `csv/` | The CSV files the page offers for download, as published |
| `charts-csv/` | The chart data files sanecite.com offers for download, as published |
| `rerun.py` | Rebuilds every file in `csv/` and `charts-csv/` from `code/site/` and `data/` and checks each byte for byte |
| `METHOD.md` | How the Lists are made, step by step |

## How to re-run a List

From the repository root, with Python 3.9 or later and nothing else installed:

    python3 lists/rerun.py

It lays out the published code and inputs like the site in a temporary folder, runs the site's own `lists.py` and
`charts.py` in their public re-run mode, and compares every file they write with the published copy here, printing one
line per file. It exits 1 if any file differs. The public re-run mode reads reply dates from `data/letters_public.json`
(delivery and reply date only, for the entries the page names or prints a reply for) and skips three checks that
guard the live site and change no output: where each reply came from, and whether each passage link lands on a
citation the checker lists. The date is pinned to the release day so the reply-window rule gives the same answer.

Code is under the MIT license (`../LICENSE`); SaneCite-made data under CC BY 4.0 (`../LICENSE-DATA`).
`SOURCES.sha256` lists each file's hash before and after staging. Paths to private working folders in the code were
replaced by `work/<name>/`; nothing else was changed. Letters to authors and the replies themselves are not published;
`csv/replies.csv` is the published summary of each reply under the right-of-reply rule.
