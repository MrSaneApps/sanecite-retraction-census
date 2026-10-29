# SaneCite citation-accuracy system: confirmatory test (pre-registered 22 Oct 2026, ~2:20 PM ET)

Written before any model runs on batch 6 and before its reference reads exist. Hashed in PREREG_HASHES.txt.

## Why

The 22 Oct rerun (PREREG_RERUN_2026-10-22.md, 18 arms on batches 2-5) showed which settings work. Combining a
screen with deciders was explored on the same data (scripts/two_stage_explore.py). Anything chosen after seeing
results must be tested on new data. This is that test.

## How the system is chosen (fixed now; applied once all 18 arms are complete)

1. Candidates: every screen arm in two_stage_explore.py (jev, clef, qwen_off, glm_off, gptoss_med, deepseek_off,
   gemma_off, kimi_off) crossed with every decider set (each single thinking arm; majority of deepseek_on, qwen_on,
   glm_on; and, once complete, majority sets that include kimi_on).
2. Screen threshold: P(major) cut that catches 90% of reference majors pooled over batches 2-5 (score_v3 rule).
3. Pick the combination with the highest kappa_major on batches 2-5 (leave-one-batch-out thresholds, as in
   two_stage_explore.py) among those whose screen flags <= 50%. Ties within 0.01: lower cost per 1,000 citations.
4. Secondary system, fixed now: the same decider set behind a Clef screen (Clef is covered by the Cloudflare grant).
5. The chosen system, its threshold and all model settings (model-cards/configs.json at that time, hashed) are
   written to SYSTEM_LOCKED_2026-10-22.md and hashed BEFORE any model call on batch 6.

## Test data: batch 6

- scripts/sample_v2.py, seed 6006, 1,000 pairs (started 2:12 PM ET). Same population and rules as batches 2-4.
- Pairs whose citing paper (PMCID) appears in batches 1-5 are dropped before reading.
- Reference: every remaining pair read blind by two readers from different model families with the same rules as
  batches 2-4 (separate Claude sessions with the v2 reading rules; Muse through judge_v2.py --models muse --prompt v2).
  Disagreements are adjudicated by a third careful read that sees both verdicts and reasons (gold.py). Readers never
  see any system output. "cannot_tell" reference items are excluded.

## Outcomes and pass bars (batch 6 only)

Primary, the chosen system versus the adjudicated reference:
- kappa for major vs not major >= 0.60;
- recall of reference majors >= 0.70 (Wilson 95% interval reported);
- precision of the system's major calls >= 0.65.
All three must hold to call the system validated. Also reported: share flagged by the screen; the system's major
rate vs the reference major rate (with intervals); kappa for any error on flagged items; cost per 1,000 citations
from billed usage; the two reference readers' agreement with each other (the ceiling).

Secondary: the Clef-screen system on the same bars; each component alone.

## What would change our minds

If the chosen system fails any primary bar, it is not used for public numbers. We then report the result, and the
next option is a stronger decider or a human read of all flagged citations. A pass validates the system against an
AI reference only; a human check of a random sample still comes before any public accuracy claim.

## Amendment 1 (22 Oct 2026, ~3:05 PM ET, before any system output or reference comparison on batch 6)

Some Claude reader runs stop partway through a packet (a safety stop in the reading tool, not a reading choice). To
keep the reference complete: packets are cut to 11 items; a part a Claude reader cannot complete is read instead by
Grok 4.7 (xAI; a different family, not a candidate system) with the same rules, through plan_calls.py. Which reader
covered each item is recorded and reported. Disagreements with Muse are adjudicated as before.

## Amendment 2 (22 Oct 2026, ~3:20 PM ET, owner rule, before the system is locked or run on batch 6)

Owner: "if there is no meaningful difference between Clef and Jev use Clef of course since it is CF native."
Step 3 of the choice rule changes: the screen is Clef (Cloudflare-native, covered by the grant) unless the best
Jev-screen system beats the best Clef-screen system with the same deciders by a meaningful margin on batches 2-5:
paired bootstrap (2,000 resamples, seed 7) 95% interval for the kappa_major difference excludes 0, or Jev catches at
least 3 more reference majors at the same precision. The Jev-screen system then becomes the secondary system on
batch 6 (swapping roles with step 4).

## Note on times (22 Oct 2026, 2:52 PM ET)

Amendments 1 and 2 were stamped ~3:05 PM and ~3:20 PM ET by mistake. By the computer's clock they were written at about 2:35 PM and 2:42 PM ET, both before any system output on batch 6 existed (none exists at the time of this note).

## Amendment 3 (22 Oct 2026, ~4:55 PM ET, before any reads of the 66 items and before any system output on batch 6)

Grok 4.7 cannot run for about two days (its plan usage window is spent). The 66 batch-6 items Claude could not
read (amendment 1) are read instead by Gemini 3.8 Flash (Google, free tier, same v2 rules and prompt, default
thinking). Its quality is measured first on 100 random batch 2-4 gold items (seed 66), reported as agreement and
kappa with gold. Grok 4.7 also reads the same 66 items when its window resets; both readings are reported, and the
primary analysis uses Gemini (Grok as sensitivity). Gemini and Gemma share a maker: if Gemma is part of the chosen
system, the primary bars are also reported without these 66 items.

## Amendment 4 (22 Oct 2026, ~5:15 PM ET, before any of the 66 items or calibration results have been looked at)

Grok 4.7 is reachable today through OpenRouter (x-ai/grok-4.7, paid per call from existing OpenRouter credits,
about $3 for 166 calls), so the amendment 1 reader is restored: Grok 4.7 reads the 66 Claude-stop items and the
same 100 calibration items (seed 66), with the v2 rules and prompt. Primary analysis uses Grok 4.7; the Gemini 3.8
Flash reads from amendment 3 are reported as a second check. The plan-based Grok job is stopped (not needed).

- Note (22 Oct 2026, ~5:22 PM ET): the free Gemini tier gave 7 calibration reads in 13 minutes (503/429), so the same model (gemini-3.8-flash) continues through OpenRouter (google/gemini-3.8-flash), same prompt; the 7 free-tier reads are kept. No results had been looked at.

- Calibration result (22 Oct 2026, 6:20 PM ET, recorded before gold for batch 6 is built): on 100 batch 2-4 gold items, Gemini 3.8 Flash exact 0.89, kappa_major 0.887 (10 majors called, 9 right); Grok 4.7 via OpenRouter exact 0.65, kappa_major 0.50 (19 majors called, 8 right). Per amendment 4, Grok stays the primary reader for the 66 Claude-stop items; every batch 6 result is also reported with Gemini in its place. OpenRouter billed $0 for all 166 Grok calls (Gemini was billed); provider details to be checked.

## Amendment 5 (22 Oct 2026, ~8:25 PM ET, before batch 6 reader disagreements are known)

Adjudication of batch 6 disagreements between reader A (Claude, or Grok for the 66 Claude-stop items) and reader B
(Muse): a third read by separate Claude sessions in 11-item packets, seeing both readers' verdicts and reasons and the item,
never any system output. Items a Claude adjudicator cannot complete (safety stop) are adjudicated by Gemini
3.8 Flash via OpenRouter with the same packet text (calibration kappa_major 0.887 vs gold). Which adjudicator decided
each item is recorded and reported. Sensitivity: primary results are also reported with Gemini 3.8 Flash in place of
Grok as reader A for the 66 items (amendment 4 note).

- Note (22 Oct 2026, ~9:30 PM ET, before any model call on batch 6): the first run of scripts/lock_system.py (kept as lock_system.py.v1) chose among all screens; amendment 2 says the screen is Clef unless Jev is meaningfully better. Corrected to the amendment as written and re-run; the best any-screen system is recorded as exploratory only.


## Amendment 6 (23 Oct 2026, ~12:05 AM ET, owner decision, AFTER the batch 6 result was known)

Owner: "yes we need human reviews but its ok to just put a small note that it's pending human review. [...]"
(an informal remark is left out here) Change to "What would change our minds": the batch 6 results are published on
sanecite.com now, marked "pending human review", instead of waiting for the human check. Nothing else changes: every
public figure says it was measured against AI reads, the human check of a random sample stays the next step, and its
result will be published beside these figures whether it confirms them or not. This amendment was made after the
result was known and is reported as such.
