# Editions

The census labels come from AI models. Models change, get new versions or disappear, so a re-run with other models,
or with the same models under a new prompt, gives other labels. This page sets one rule for that.

## The rule

1. **A new model or a new prompt makes a new edition.** Changing any panel model, its version, the prompt, the
   examples, the answer options or the codebook starts edition N+1. So does adding a reader to the panel.
2. **Editions are never mixed.** An edition's labels are analysed only with labels of the same edition. No result
   pools labels from two editions. The scripts enforce this: `scripts/stage3_census.py` will not add rows of another
   edition to a label file, and `scripts/analyze_census.py` stops if one analysis would use labels from two.
3. **Old editions are frozen.** Their files, hashes (`MANIFEST.sha256`) and results stay as released. A later edition
   never overwrites them; it gets its own data folder, its own result file and its own release.
4. **A correction is not an edition.** Fixing a known error in an edition's data or analysis (such as the 20 Oct 2026
   wrong-record correction in `errata/`) is a dated correction of that edition. It is published beside the original
   figures, which stay visible.
5. **Each edition says what it is.** Its release notes name the models (with version or date where the provider gives
   one), the codebook version, the prompt hash and the run dates, and compare its headline with the previous edition.

## What each label records

From 23 Oct 2026, every label row that `scripts/stage3_census.py` writes carries:

| Field | What it is |
|---|---|
| `model_id` | The model asked, as named by its provider |
| `version` | The version the provider reported, where it reports one |
| `run_date` | The UTC day the run started |
| `prompt_sha256` | SHA-256 of the codebook version, system prompt, examples and answer options |

## Edition 1

The census released on 14 Oct 2026 (codebook v3.3): Jev (`typesafe/jev`), Clef (`@cf/cloudflare/clef`) and Gemma (`@cf/google/gemma-4-26b-a4b-it`), run
13-14 Oct 2026. Its label rows predate the fields above. The models and prompts are fixed by the code hashes in
`MANIFEST.sha256` and the protocol amendments in `PROTOCOL.md`.
