# Deviations from PROTOCOL.md (logged as they happen, before any analysis)

1. 21 Oct 2026, 20:50 ET, after 381 of the first 531 calls: the shared spend guard reserves a worst-case cost per call
   for 5 minutes, and the harness's output caps (gpt-oss 12,000 tokens, gemma 2,500, nemotron 8,000) pushed those
   reservations past the $12.50 hourly ceiling while real spend was $0.09. Changed: output caps to 4,000 / 1,500 /
   1,500 tokens (answers seen so far are about 120-1,500 tokens); a guard refusal now waits 30 s and retries instead of
   counting as a failed try; judge workers 12 -> 6. Also fixed: usage (prompt and completion tokens, neurons) was not
   being saved (the harness returns pt/ct/neurons at the top level, not under "usage"); cost for calls before this
   fix comes from Cloudflare's usage record. Prompt, models and scoring are unchanged. Answers already given are kept.

2. 22 Oct 2026, 6:07 PM ET, stage 3 rerun (PREREG_RERUN_2026-10-22.md), audit fix, no rule change. scripts/score_v3.py
   did not compute two things the rerun pre-registration requires: the AUC for any error (major + minor) vs accurate,
   and cost per 1,000 citations. Added: auc_error per fold and pooled, scored by P(major) + P(minor) per sample
   (votes when there are no logprobs), plus a secondary Clef vs Jev bootstrap on it; cost from a dated, sourced
   --prices file (no price is written into the code; with none the cost shows "not recorded", never 0; Jev cost
   must come from the AI Gateway billing record, not logged tokens). Also: an arm with a batch absent or items
   missing is marked incomplete and its pass_screen is None instead of True/False; _rows keep full precision; the
   bootstrap reports its valid resamples; neurons are summed. Added after the 11:30 AM and 2:00 PM interim looks,
   which showed only the major AUC. The threshold rule, bars, kappas and P(major) score are unchanged: every value
   the old scorer reported for runs/full is identical (503 checks, audit-20261022/test_score_v3.out), except
   pass_screen on the partial kimi_on arm. Old file: scripts/score_v3.py.bak-audit (sha256 2ee36659..., the
   registered hash). New sha256 in PREREG_HASHES.txt.

3. 22 Oct 2026, 6:55 PM ET, stage 3 rerun, recorded after the fact by the audit. Jev b4 output from 10:31-10:32 AM
   was discarded after at least 11 TypeSafe direct-API fallbacks and re-run with TYPESAFE_API_KEY unset; the route for
   Jev b2, b3 and the first 64 b5 items is unverified. Details and how to settle it: PREREG_RERUN Amendment 8.
   Every scoring look so far, and which output is primary for the six logprob arms: PREREG_RERUN Amendment 7.

## Batch 7 answer key (PREREG_REFSET_B7_2026-10-31.md), registered 31 Oct 2026, 9:16 AM ET (census repo commit 628db50)
1. 31 Oct, 9:25 AM ET, before any Part A sampling output or any reader output was looked at. The canary is submitted
   as its own Message Batch (batch label b6, ANTHROPIC_TAG -b7) at the same time and with the same settings as the
   Part A first reads, not inside the same Message Batch: `anthropic_read.py` takes one sample source per submit.
   The canary's purpose (same reader, same settings, same day) is unchanged.
2. 31 Oct, 9:25 AM ET, same status. Part B reader 2 (Muse) started on 31 Oct, 9:18 AM, as soon as the Part B draw was
   hashed, instead of Thu 5 Nov in RUN_PLAN.md (the Muse budget is 200 calls an hour day and night). Order and rules
   unchanged. Part B reader 1 (Opus) spend stop for its own state file set to $27, the worst case with every reply at
   max_tokens (expected about $3); the $40 batch 7 stop on `anthropic_read.py` label b7 is unchanged.
3. 31 Oct, 9:44 AM ET, before any reader output. Part A first reads go in two Message Batches of 660 (draws sorted,
   first and second half; tags -b7h1 and -b7h2), the second submitted after the first is collected: the spend stop
   books three times the likely cost of a batch, and one batch of 1,320 ($17.80 likely) would book $53 against the
   $40 stop. Same model, effort, prompt and items; the $40 stop is unchanged. The canary went at 9:43 AM (tag -b7).
4. 31 Oct, 9:55 AM ET, after the canary result and before any other batch 7 result. The canary read 31 of 33 (2 Claude
   refusals, draws 1661 and 1775, not re-sent) and all 31 match batch 6 gold, so 31 of 33 match: the stop rule (27)
   and the pooling tolerance (28) both pass as section 3 words them. `score_b7.py` had coded the tolerance as "all 33
   read and at least 28 match", stricter than the registered text; it now counts matches out of 33, with a refusal as
   a miss. Re-hashed. The batch 6 test output is unchanged.
5. 2 Nov, 3:34 AM ET, before any scoring run and before the adjudicated key was built. `score_b7.py` read third-read
   verdicts only from a nested "parsed" field, but `gemini_read.py` and `openrouter_read.py` (the registered third-read
   hosts) write the verdict at the top level, so the Part A 2-of-3 sensitivity would have been skipped without a
   message. It now reads either form. No other line changed. Re-hashed. Also recorded: the free Gemini key's quota for
   `gemini-3.8-flash` is now 20 requests a day (Google 429 text, 2 Nov 3:40 AM: "generate_content_free_tier_requests,
   limit: 20"), not the ~125 a day seen in October. Third reads stand at 21 of 213 on host 1; the run is stopped, not
   failed through. Host 2 (OpenRouter, paid) needs the owner's yes under section 5.
6. 5 Nov 2026, 9:01 PM ET, before any scoring run. Owner: "i approve the open router payment" (host 2 under section 5). 192 third reads remain of 213 (21 done on host 1). Same model (google/gemini-3.8-flash), rules, user message and call: batches/b7/adj/run_third_or.py imports call() from scripts/openrouter_read.py unchanged. One change, the retry loop: after the 5 Nov Muse account block, the first blank, refusal or off-list answer sets that draw aside with no retry, two set-asides end the run, and a provider refusal status ends it at once. Only rate limits and outages retry. Spend stops at $1.95, the amount the owner saw. A draw set aside has no third read and is reported as coverage, not as a verdict.
