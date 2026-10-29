# Pre-registration: stage 3 rerun, every model configured from its card (22 Oct 2026)

Written before any rerun call was scored. Hash in PREREG_HASHES.txt.

## What runs
- Models and settings: MODEL_CARDS_2026-10-22.md, generated from model-cards/configs.json (the file judge_v3.py
  runs from). 18 arms: thinking off and on for Kimi K2.6, DeepSeek V4.1 Flash, Qwen 3.8, GLM 5.2, Gemma 4,
  Nemotron 3; gpt-oss-120b at reasoning medium and high; Llama 3.3 70B; Mistral Small 3.1; Clef and Jev with the
  verdict options rotated 4 ways. Same v2 prompt and excerpts as overnight; only settings change.
- Items: every judgeable reference citation in b2 (200), b3 (150), b4 (150) and b5 (150), with each batch's own
  sample file and draw list.
- Parse check first: 20 b2 citations per arm. Bar: zero bad parses and zero replies cut off. An arm that fails is
  fixed (call shape) and re-checked; it is never dropped without the fix attempt and the transcript on file.

## Score
- Chat arms: score = mean over samples of p_i; p_i = P(major) from the verdict token's top_logprobs when returned,
  else 1 if that sample says major, else 0.
- Typed arms (Clef, Jev): mean P(major) over the 4 option orders.
- Reference: adjudicated gold (b2-b4), Claude reference (b5). Reference "cannot_tell" citations are excluded.

## Rule and tests (leave one batch out)
- For each held-out batch, pick on the other three batches pooled the highest threshold t that catches >= 90% of
  their reference majors. Apply t to the held-out batch. Report per fold: majors caught, share flagged.
- Screen bar (pass): pooled over the four held-out folds, catches >= 90% of reference majors and flags <= 50%.
  Wilson 95% interval on recall reported.
- Ranking: AUC for major vs not-major, and for any error (major + minor) vs accurate, per batch and pooled.
- Decide-alone bar (reported for every arm): majority verdict across samples (typed: top probability averaged over
  orders) vs reference: Cohen's kappa for error vs no error >= 0.5 and for major vs not major >= 0.6.
- Every arm and fold is reported, failures included, with bad-parse counts, tokens and cost.
- Clef vs Jev: compared on the same items by pooled held-out recall and flag rate, AUC (paired bootstrap, 2,000
  resamples, 95% interval on the AUC difference) and cost per 1,000 citations.

## Not decided here
Panels (combinations of arms) are exploratory after this; any panel claim needs a fresh batch (b6+).

## Amendment 1 (22 Oct, 9:59 AM ET, before any rerun output)
Thinking-on arms no longer request logprobs. Smokes: Gemma and Kimi with thinking on, n=3 and logprobs together hit
Cloudflare 408 timeouts after 235 s (3 of 3 tries); each setting alone, and each pair, passed in 15 s
(logs/smoke_*.log, model-cards/probe/). Research (set A) says verdict-token logprobs after reasoning sit near 1, so
these arms are scored by vote share over their samples, as the score rule already does when logprobs are absent.

## Amendment 2 (22 Oct, 10:09 AM ET, before any rerun output)
Kimi thinking-on gets its 3 samples from 3 separate calls ("repeats": 3), not n=3 in one request: with thinking on,
n=1 passed in 15 s; n=3 failed (408 at 235 s, then 500 at 91 s). Settings per call are unchanged.
Gemma thinking-on with n=3 passed alone (15 s) and failed only when nine smokes ran at once; it keeps n=3, and
failed calls are retried by judge_v3 and counted.

## Amendment 3 (22 Oct, 10:14 AM ET, before any rerun output is scored)
GLM 5.2 thinking-off arm uses chat_template_kwargs.enable_thinking false, not reasoning_effort none. Parse check:
with reasoning_effort none it still reasoned (1,339 completion tokens, 5,974 characters of reasoning on draw 862);
with enable_thinking false it gave 56 tokens and no reasoning. The parse-check glm_off output is discarded.
Checked for every other off arm: median completion 98-152 tokens (no reasoning). gpt-oss high used ~40% more tokens
than medium, so reasoning.effort is read.

## Amendment 4 (22 Oct, 10:25 AM ET, before any rerun output is scored)
Gemma thinking-on also gets its 3 samples from 3 separate calls: with n=3 and 6 workers the parse check finished 3 of
20 citations in 14 minutes (Cloudflare 235 s timeouts); Kimi with separate calls finished 10 in the same time.
Settings per call are unchanged. The n=3 parse-check output for gemma_on is discarded.

## Amendment 5 (22 Oct, 10:33 AM ET, before any rerun output is scored)
A reply with a valid verdict but an off-list citation_type counts by its verdict (the only field the score uses);
citation_type is recorded as None with the off-list value kept. Cause: Mistral Small 3.1 wrote citation_type
"cannot_tell" on b2 draw 2608 (3 of 3 samples, also overnight); guided_json did not constrain it on Cloudflare.
Applies to every arm; items that failed only this way are re-judged at the end.

## Amendment 6 (22 Oct, 11:24 AM ET, after an interim look at 8 finished arms; the rule is unchanged)
judge_v3.verdict_logprobs rounded each P(verdict) to 5 decimals. Confident non-major calls became exactly 0, so scores
tied at 0 and the leave-one-batch-out rule chose t = 0 (flag everything) for Gemma and Nemotron thinking-off. This is a
storage bug, not a model property. Fix: full precision. Every logprob arm (kimi_off, deepseek_off, qwen_off, glm_off,
gemma_off, nemotron_off) is re-run in full; the rounded outputs are kept in runs/full/discarded_rounded/ and both are
reported. The interim look: score_partial_1130.json (Jev and Kimi-off passed; Clef 35/39 missed by one major).

## Amendment 7 (22 Oct, 6:55 PM ET; audit entry written AFTER five scoring looks; the rule, bars, kappas and score are unchanged)
Written by the 22 Oct research-validity audit to record every look so far. It is not a pre-registered choice.
(a) Looks, in order, with each file's sha256:
- 11:23 AM, runs/full/score_partial_1130.json (50750de23c0f2b2cf8f50e8cfef417dc55878d2c9c53f56e2d88edd74e0adab1),
  8 arms, rounded logprobs. Pooled held-out majors caught / flag rate / screen bar: clef 35/39, 23.5%, fail;
  jev 36/39, 18.3%, pass; kimi_off 36/39, 22.3%, pass; gemma_off 39/39, 100%, fail; nemotron_off 37/39, 67.7%, fail;
  nemotron_on 39/39, 100%, fail; llama 39/39, 100%, fail; mistral 39/39, 100%, fail. Also seen: Clef vs Jev AUC
  difference -0.023 (95% CI -0.049 to 0.001) (handoff, 11:35 AM update). Amendment 6 named only three of these.
- 1:54 PM, runs/full/score_interim_1400.json (3744edac398375ca236dde358b74c1990da2e8b0eeda26833dc838fc175de791),
  16 arms. Full-precision re-runs complete for deepseek_off, qwen_off, glm_off, gemma_off, nemotron_off; kimi_off
  partial (471 items, 111 missing). Pass: jev 36/39 18.3%; qwen_off 36/39 30.0%; gptoss_med 36/39 44.7%. Fail:
  clef 35/39 23.5%; kimi_off 22/26 14.7% (partial); deepseek_off 35/39 36.4%; deepseek_on 39/39 100%; qwen_on 39/39
  100%; glm_off 35/39 18.3%; glm_on 35/39 52.4%; gemma_off 35/39 30.2%; nemotron_off 36/39 69.2%; nemotron_on 39/39
  100%; gptoss_high 39/39 100%; llama 39/39 100%; mistral 39/39 100%.
- 2:11 PM and 2:54 PM, runs/full/two_stage_explore_interim.json
  (3636fe69e261e1cdd9c7bcfc15fee7fdbc73f0479e7cf7e00f594787c35a7f38) and runs/full/two_stage_explore_1455.json
  (e3844058e015246124d0114537788dc0559f5676e69e829f7a1c62726cb67c25): exploratory two-stage combinations on the same
  items (PREREG_SYSTEM). They are not tests of this registration. PREREG_SYSTEM was written after these looks.
- 6:04 PM, audit-20261022/score_before.json (8cdf0cc233f739fd8cbf70c58146e8698adbb323bdc8ea5ede97df782a50c7c5):
  audit regression run of the old scorer over every arm on disk (DEVIATIONS item 2), used to check that the
  corrected scorer reproduces the old values. kimi_on was partial (332 items).
(b) Primary output: for the six logprob arms (kimi_off, deepseek_off, qwen_off, glm_off, gemma_off, nemotron_off)
  the full-precision re-run is primary, whatever its result; the rounded outputs in runs/full/discarded_rounded/ are
  secondary and are reported only as the record of the storage bug. Reason: Amendment 6 (11:24 AM) found the rounding
  was a storage bug, before any re-run output existed. Said plainly: this line was written after full-precision
  results for five of the six arms had been seen (1:54 PM look). Owner to confirm.
(c) From now on: the next scoring of these arms is the final one, after kimi_on and the Amendment 5 re-judge pass
  finish. Any other look is listed here, with its file and sha256, before its numbers are used. A parse or
  completeness check that reports no pass/fail, recall, AUC or kappa is not a look.

## Amendment 8 (22 Oct, 6:55 PM ET; audit entry; a deviation recorded after the fact)
Jev b4 was run twice. First run 10:31:36-10:32:06 AM: Cloudflare returned 429s and model_calls.jev served at least
11 calls through TypeSafe's direct API ("jev-latest", which may be a different Jev version) (logs/full.log, 11
JEV-DIRECT-FALLBACK lines, all b4). That output is kept, unscored, in runs/full/discarded/jev_b4_fallback_mixed.jsonl.
run_arms.sh was then edited (10:32:33) to unset TYPESAFE_API_KEY; b4 was re-run 10:32:35-10:33:57 and the remaining
86 b5 items 10:33:57-10:34:28 (logs/full_jev2.log). b2 (200 items, 10:30:04-10:31:08), b3 (150, 10:31:08-10:31:36)
and the first 64 b5 items (10:32:06-10:32:18) ran with the key still set. The logs show no fallback line for them,
but this does not prove the route: run_arms.sh keeps only lines matching STAGE|FAIL|DONE|Error|Traceback, so a
fallback whose error text lacks "Error" (a timeout, a bad reply shape) would not be logged, and the rows record only
model "typesafe/jev", not the route that answered. Status: route for those 414 items is unverified. To settle it, the
owner checks AI Gateway and TypeSafe usage for 10:30-10:35 AM ET (read-only), or those items are re-run with the key
unset (card-paid; owner's go). Until then every Jev result carries this caveat. The staged
audit-20261022/judge_v3.proposed.py records the route and served model on every sample; it is applied only between
runs, never while arms are running.
