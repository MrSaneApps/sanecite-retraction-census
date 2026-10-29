# Stage 3 tuning results, night of 21-22 Oct 2026 (Claude)

Pre-registration: PROTOCOL.md, PROTOCOL_TUNING_2026-10-22.md (amendment 1), METHOD_CHOSEN_2026-10-22.md (choice 1),
METHOD_CHOSEN_v2_2026-10-22.md (choice 2), METHOD_CHOSEN_v3_2026-10-22.md (choice 3); hashes in PREREG_HASHES.txt.
Success bar (all tests): kappa_error >= 0.5 and kappa_major >= 0.6 against the batch's reference set.
Reference sets: 150-200 random pairs per batch, read blind by separate Claude sessions and Muse with the same rules, every
disagreement adjudicated (batch 5: Claude only, because Muse is part of method 3).

## Outcome: no automated method passed its fresh test

| Method | Chosen on | Test batch | kappa_error | kappa_major | Pass |
|---|---|---|---|---|---|
| 1. Plurality of 5 cheap models | batch 2 gold | batch 3 | 0.296 | 0.493 | no |
| 2. Twostep vote of 5 cheap models | worst of b2+b3 | batch 4 | 0.580 | 0.366 | no |
| 3. Method 2 screens, Muse re-reads flagged 27-34% | b2-b4, post hoc | batch 5 | 0.498 | 0.471 | no |

Why (evidence):
- Two strong readers (Claude, Muse) agree with each other at kappa_error 0.58-0.75, kappa_major 0.74-0.85 (b2-b4).
  The cheap panel reaches 0.35-0.70 on major against either reader: it finds about 8 in 10 major errors but calls
  about three times too many (precision 0.27 on batch 4).
- Each 150-pair reference holds only 5-13 major errors, so kappa_major swings widely between batches (batch 5: 10
  reference majors; method 3 called 6, 4 in common). Tuning on sets this small overfits; three fresh tests showed it.
- Wall: better results now need a bigger reference set with a human check, not more vote rules.

## Best current estimates (reference reads, not the automated panel)
**Audit note, 22 Oct 2026, 7:00 PM ET:** the 6.2% (and 18.9%) is a post-hoc pooled estimate from AI reference reads
(Claude and a second model family, disagreements settled by a further Claude read). Its samples and reading rules were
fixed in advance, but pooling them into a rate was not in the plan; the registered primary estimate of this pilot is
still 10.8% (PROTOCOL.md, Analysis 2). Neither has been checked by people. Outbound text copies the long form in
SANECITE_SOP.md (facts sheet) and never calls 6.2% "pre-registered".
Pooled batches 2-4 gold (500 random citations, 471 judgeable):
- any error 89/471 = 18.9% (95% CI 15.6-22.7%); major 29/471 = 6.2% (4.3-8.7%).
- specific_claim citations (219): any error 25.1%, major 7.8%. background (185): 15.7%, 5.4%.
  method_or_tool (56): 8.9%, 3.6%. data_source (11): 0, 0.
- Batch 5 Claude reference (142 judgeable): any error 25, major 10 (7.0%).
- Human meta-analysis for comparison: 25.4% any, 11.9% major (Jergas & Baethge, PeerJ 2015, doi:10.7717/peerj.1364).

## Relation to the stage 3 pilot (RESULTS.md)
The pilot reported 10.8% major (95% CI 9.3-12.6%) from a different 3-model panel and an older retrieval step; its own
blind Claude read of 100 pairs matched the panel (8.2% major on 85 pairs, 95% CI about 4-16%). The reference reads here
are larger and adjudicated and give 6.2% (4.3-8.7%). Use 6.2% as the current best estimate; the gap may come from the
panel, the retrieval change or chance.

## What works today
SUPERSEDED (audit note, 22 Oct 2026, 7:00 PM ET): the overnight screening figures below ("about 8 in 10", "about $3
per 1,000") come from runs the rerun plan found misconfigured (thinking off, scored by top verdict only). Do not quote
them. Quote recall, flag rate and cost only from the scored rerun (score_v3 output, with Wilson intervals) and the
batch-6 system test, and say the reference is AI, not human.
- Screening: the panel flags about 1 in 3 citations and catches about 8 in 10 of the major ones, for about $3 per
  1,000 citations. Flags need a strong reader or a person to confirm.
- Next: a human-labelled set of about 500 citations (enough for 30+ majors) to set the bar and train the vote rule.

Scripts: run_batch.sh, judge_v2.py, panel_rates.py, threshold_grid.py, robust_pick.py, gold.py, ref_packets.py.
Data: batches/b2-b5 (sample, voters, ref, ref_muse, gold, rates_v2panel.json, stage2_muse).

## Clef screen, pre-registered fresh test (22 Oct, 9:04-9:07 AM ET) — PASSED
Batch 2 had used Clef by its top choice only; our SOP says Clef needs its own confidence bars. Rescored by P(major),
batch 2 gave AUC 0.92. Rule fixed before the run (PREREG_CLEF_SCREEN_2026-10-22.md, hash in PREREG_HASHES.txt):
flag when P(major) >= 0.10; pass = catch >= 90% of reference majors while flagging <= 50%.
- Test, b3+b4 pooled (281 judgeable, 16 majors): caught 15/16 (94%), flagged 46%; AUC major 0.925. PASS.
  At 0.12: 15/16, flagged 36%.
- Batch 5 (Claude reference, 142 judgeable, 10 majors): caught 10/10 at both cutoffs; flagged 41% / 29%. AUC 0.95.
- All fresh batches: 25 of 26 majors caught. The one miss (b4 draw 2723, P 0.077) was a split call settled by
  adjudication: the citing paper credited VR for gains the study tied to separate training.
- Cost: about 2,500 input tokens per citation, about $0.60 per 1,000 citations at list price (grant-covered now).
- Use: Clef screens every citation; a frontier reader reads the flagged 30-45%; people check a sample.
- Script: scripts/clef_test_score.py; data batches/b3-b5/bake_clef/. Reference sets are AI (Claude + Muse, adjudicated),
  not yet human-checked.
