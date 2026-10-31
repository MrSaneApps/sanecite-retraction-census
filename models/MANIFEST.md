# models/ manifest

Each file, the internal record it was copied from, and what changed. Numbers are unchanged in every file.

| File | Source record | Change |
|---|---|---|
| README.md | written for this folder | new |
| MANIFEST.md | written for this folder | new |
| scoreboard.csv | the full internal scoreboard, same rows | record and already_public columns dropped; public_record added; host, cost and model wording made public |
| pilot_bakeoff_v1_scorecard.json | Phase 2 pilot bake-off v1 scorecard, 13 Oct 2026 | added _note (set, key, Clef price); Cloudflare model ids written without the leading at-sign; quote-share metric renamed verbatim_evidence_share |
| pilot_holdout_score.json | Phase 2 pilot blind holdout score, 13 Oct 2026 | none (byte content re-serialised) |
| pilot_holdout_labels.json | Phase 2 pilot blind holdout labels by item number, 13 Oct 2026 | labeller reworded |
| pilot_cost.json | Phase 2 pilot labelling cost record, 13 Oct 2026 | Cloudflare model ids written without the leading at-sign |
| census_dev_v3_key.json | census development key (130 pairs, Claude labels), 13 Oct 2026 | codebook note reworded (first person removed) |
| census_dev_v3_labels.jsonl | census development labels from Clef, Gemma 4 and Jev, 13 Oct 2026 | quote field dropped (187 of 537 rows had one); Cloudflare model ids written without the leading at-sign |
| census_dev_v3_labels_kimi.jsonl | census development labels from Kimi K2.6, 13 Oct 2026 | quote field dropped (175 of 175 rows had one); Cloudflare model ids written without the leading at-sign |
| stage3_pilot_results.json | stage 3 pilot results, 21 Oct 2026 | Cloudflare model ids written without the leading at-sign; quote-share metric renamed verbatim_evidence_share |
| stage3_pilot_blind_compare.json | stage 3 pilot panel vs blind read, 21 Oct 2026 | none |
| stage3_b2_bake_superseded.json | stage 3 overnight batch 2 evaluation, 21 Oct 2026 | added _note (superseded settings) |
| stage3_rerun_scoring_look_20261022.txt | stage 3 rerun scoring look, 22 Oct 2026, 6:04 PM ET | added header note |
| tuning_single_readers_20261030.json | 30 Oct 2026 tuning score file (single readers) | added _note |
| tuning_composer_b6_score.json | 30 Oct 2026 Composer 2.5 batch 6 score | added _note |
| census_reader_check_gemini_panel.json | 29 Oct 2026 census reader check, Gemini panel | keys renamed (internal prefix and panel names), _note added |
| census_reader_check_muse.json | 29 Oct 2026 census reader check, Muse Spark (Meta) | keys renamed, _note added |
| census_reader_check_claude_api.json | 30-31 Oct 2026 census reader check, Claude API | panel key renamed, empty panel entry dropped, _note added |
| score_reader_check.py | 31 Oct 2026 Lists reader-check scorer | header comment added; renamed |
