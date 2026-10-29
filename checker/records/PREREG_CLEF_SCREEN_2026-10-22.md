# Pre-registration: Clef as a screen for serious citation errors (22 Oct 2026, written before any new Clef run)

Why: Clef was used on batch 2 by its top choice only. Our SOP says Clef needs its own confidence bars. Rescoring the
saved batch 2 answers by P(major) gave AUC 0.92; P(major) >= 0.10 caught 13/13 reference majors and flagged 47%;
>= 0.12 caught 12/13 and flagged 35%. Those cutoffs were chosen on batch 2, so they must be tested fresh.

Rule (fixed now): same call as batch 2 (judge_v2.py --prompt v2, model @cf/cloudflare/clef). Flag a citation when
Clef P(major) >= 0.10. Secondary, reported but not the test: >= 0.12.
Test set: batches b3 + b4 pooled, against their adjudicated reference (gold/gold.jsonl), cannot_tell excluded.
Pass: catches >= 90% of reference majors AND flags <= 50% of citations.
Report also: AUC for major and any error, majors caught at each cutoff, flagged share, and batch 5 vs Claude reference
if it can be scored.
