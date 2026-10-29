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
