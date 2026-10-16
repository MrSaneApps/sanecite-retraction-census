# SaneCite retraction census: protocol

Analysis protocol for the SaneCite census of citations to retracted papers, registered before the final analysis.
Start with `PROTOCOL.md`. `MANIFEST.sha256` fixes the scripts and data that existed at registration.
Results and the full data will be published at https://sanecite.com/data.html.

## Data release (amendment 3, 14 October 2026)

`data/` holds the census: `stage1_papers.jsonl.gz` (the frame: 22,553 retracted papers with Retraction Watch reason,
dates and later-citation counts), `stage2_v31.jsonl.gz` (every extracted citing passage), `stage3_{jev,clef,gemma}.jsonl.gz`
(each model's answer per passage), `census_rows.jsonl.gz` (the label per citing pair), `citer_meta.jsonl.gz` (Europe PMC
metadata for all 130,315 later citations), the result files, `paper_numbers.md` (every figure the paper quotes) and
`synthesis_check_verified.json.gz`. Re-run with `SANECITE_DATA=<dir> python3 scripts/analyze_census.py` and the other
scripts listed in `PROTOCOL.md`. Hsiao and Schneider's data are not redistributed here (Illinois Data Bank,
doi:10.13012/B2IDB-8255619_V2).

All figures are provisional until the human labelling round (`human_labels/`; workbooks from `scripts/human_sheets.py`,
scoring fixed in advance in `scripts/human_score.py`, see amendment 4). Citing passages are short quotations
from open-access papers in Europe PMC, included so each label can be checked against its text.

## Code release (amendment 5, 16 October 2026)

All the code is now public. `phase1/` holds the Phase 1 count of citations to retracted papers (262,998 on the
16 October snapshot, with the administrative rule Phase 2 uses); see `phase1/README.md`. `scripts/model_calls.py`
is the public copy of the two model-call helpers that were private, so `scripts/classify.py` and
`scripts/stage3_census.py` run from this repository alone. It needs a Cloudflare account (`CLOUDFLARE_API_TOKEN`,
`CLOUDFLARE_ACCOUNT_ID`).
