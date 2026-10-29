# Method choice 2 (amendment 2), 22 Oct 2026, 2:50 AM ET, before any batch 4 sampling or judging

## What happened to choice 1
The panel picked on batch 2 gold alone (plurality of 5) failed the pre-registered bar on batch 3 gold:
kappa_error 0.296 and kappa_major 0.493 (bar 0.5 and 0.6), against 0.530 and 0.801 on batch 2. Choosing among about
6,000 panel and vote-rule combinations with 200 reference items overfit. Reported as a failure.

## Choice 2
Rule: rank every panel and vote rule by the WORSE of its two scores (kappa_error + kappa_major) on batch 2 gold (200)
and batch 3 gold (150); pick the top.
Chosen: twostep vote of 5 voters: deepseek-v4.1-flash (prompt v2), kimi-k2.6 (v2), gpt-oss-120b (v3),
llama-3.3-70b-instruct-fp8-fast (v3), qwen3.8-27b (v3).
Batch 2 gold: kappa_error 0.497, kappa_major 0.703, cannot_tell 6 of 200.
Batch 3 gold: kappa_error 0.539, kappa_major 0.693, cannot_tell 8 of 150.
Twostep: error vs accurate by majority of voters that judged (cannot_tell abstains); if error, major when at least half
of the error votes say major; a tie or no judging votes = cannot_tell.

## Test (batch 4, seed 4004, 1,000 pairs) and its gold (150 pairs, seed 44; Claude + Muse blind, adjudicated)
Same success bar as amendment 1: kappa_major >= 0.6 and kappa_error >= 0.5 on batch 4 gold.
Rates reported with Wilson 95% CIs next to batches 2 and 3 judged by the same panel.
