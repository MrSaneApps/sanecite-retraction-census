# Flags: the census flags, per citing paper

The flag files sanecite.com/data serves, staged by `scripts/stage_release.py` on 2026-11-09 from the site at c4c1349.

| Path | What it is |
|---|---|
| `flags_by_paper.csv` | One row per citing paper with a flag: its DOI, PMID and PMCID, whether it cites a retracted paper as support, how many citations of each kind, and the DOIs of the retracted papers it cites as support |
| `flags_by_paper.summary.json` | The totals of that file |
| `schema/v0.json` | The open flag format, version 0 (JSON Schema), also at sanecite.com/flag-schema/v0.json |
| `schema/example.jsonl` | Example flags in that format |

The flags are the census readings after every published correction, the same rows the Lists are built from
(`../lists/data/list_corrections.json` lists each correction, with its sources). They are AI readings, pending human
review. Data under CC BY 4.0 (`../LICENSE-DATA`).
