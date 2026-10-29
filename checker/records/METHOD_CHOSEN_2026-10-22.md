# Method chosen on batch 2 gold (amendment 1), 22 Oct 2026, 1:35 AM ET, before any batch 3 scoring

Gold: 200 batch 2 pairs; Claude and Muse agreed on 172 (86%); 28 adjudicated by a third Claude read.
Gold verdicts: accurate 153, minor 24, major 13, cannot_tell 10.

Rule: highest kappa_error + kappa_major over all 3-5 voter panels and 4 vote rules.
Chosen: plurality vote of 5 voters: deepseek-v4.1-flash (prompt v2), gpt-oss-120b (v2), kimi-k2.6 (v2),
llama-3.3-70b-instruct-fp8-fast (v2), gpt-oss-120b (v3). No majority = cannot_tell.
Batch 2 gold: kappa_error 0.530, kappa_major 0.801, panel major rate 7.4%, any-error rate 12.1%, cannot_tell 35 of 200.
Runner-up: twostep, 4 voters (llama v2, mistral v2, qwen3.8 v2, gpt-oss v3): 0.501 / 0.783.
