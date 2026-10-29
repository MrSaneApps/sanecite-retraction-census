# Checker: the citation-accuracy test (batch 6)

The test of 996 random citations behind the accuracy figures on sanecite.com/checker, as recorded. Staged by
`scripts/stage_release.py` on 2026-10-29.

| Path | What it is |
|---|---|
| `records/PROTOCOL.md`, `records/PREREG_*.md` | The test plan and the pre-registrations, with their dated amendments |
| `records/DEVIATIONS.md` | Every departure from the plan |
| `records/PREREG_HASHES.txt` | The hash log. It says itself which hashes were recorded after the fact and that amendments 1-6 to the rerun plan were made without a hash each |
| `records/SYSTEM_LOCKED_2026-10-22.json` | The checker as locked before any model call on batch 6 |
| `records/B6_RESULT_2026-10-22.*` | The scored result |
| `reads/` | The reference reads: reader A, reader B, the adjudicated items and the final reference (`gold.jsonl`) |
| `items.csv` | One row per citation: identifiers, both readers, the reference, the screen scores, each decider's vote and the system's call |
| `scripts/` | The sampling, reading, scoring and locking scripts |

Records and reads are copied byte for byte unless listed below, so `shasum -a 256` on them matches the latest hash
`PREREG_HASHES.txt` gives for them (paths in the log are relative to the original working folder). Some hashes in the
log were recorded after the fact, and the log says so on those lines: amendment 6 to `PREREG_SYSTEM_2026-10-22.md`
(23 Oct 2026, the decision to publish the batch 6 result marked "pending human review") was written after the result
was known and hashed the next day. Scripts had private folder paths replaced by `work/<name>/`; `SOURCES.sha256` gives
each file's hash before and after. The citing and cited passages the readers saw are not included (they are other
authors' text); `items.csv` gives the PMC and PubMed IDs to find them.

Files that differ from the original, and why (the original's hash is in `SOURCES.sha256`; the
originals can be shown on request):

- `reads/ref_gemini.jsonl`: the quoted passages from the papers ("quote" fields) are left out
- `reads/ref_grok_or.jsonl`: the quoted passages from the papers ("quote" fields) are left out
- `reads/ref_muse_muse.jsonl`: the quoted passages from the papers ("quote" fields) are left out
- `records/MODEL_CARDS_2026-10-22.md`: a private folder path replaced; internal tool, machine and procedure names replaced
- `records/PREREG_SYSTEM_2026-10-22.md`: an informal remark left out; internal tool, machine and procedure names replaced
- `records/PROTOCOL_TUNING_2026-10-22.md`: internal tool, machine and procedure names replaced
- `records/TUNING_RESULTS_2026-10-22.md`: internal tool, machine and procedure names replaced
- `records/run.sh`: a private folder path replaced
- `records/run_batch.sh`: a private account ID and a private secret loader removed; a private folder path replaced

All reads are by AI models; no human has checked them yet. Code MIT, data CC BY 4.0 (see the repository root).
