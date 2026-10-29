# Stage 3 pilot results: are ordinary citations accurate? (21 Oct 2026, provisional, AI-judged)

> **Update, 22 Oct 2026, 11 PM ET:** the pre-registered batch 6 test supersedes the figures below. On 996 fresh
> citations (915 judgeable), the adjudicated two-family AI reference found 7.2% major (66 of 915; 95% CI 5.7-9.1%)
> and 20.3% any error (186 of 915). The locked checker (Clef screen, then DeepSeek, Qwen and GLM voting) passed all
> three bars: recall 84.8% (56/66), precision 69.1% (56/81), kappa_major 0.741 (reference readers agree at 0.658).
> AI reference only; a human check of a sample comes before any public accuracy claim. See B6_RESULT_2026-10-22.md.

> **Update, 22 Oct 2026, 4:55 AM ET:** larger reference sets read overnight (500 random citations, two blind readers from different AI families, disagreements adjudicated) give a lower major rate: 6.2% (95% CI 4.3-8.7%), with 18.9% any error. The pilot panel matched a single blind read here (8.2% on 85 pairs, 95% CI about 4-16%), but those batches also used a newer retrieval step (sample_v2.py), so the two estimates are not strictly comparable. Low-cost panels tested overnight called major errors 2-3 times as often as the reference readers. Use 6.2% as the current best estimate. See TUNING_RESULTS_2026-10-22.md.

> **Audit note, 22 Oct 2026, 7:00 PM ET:** the 6.2% (and 18.9%) is a post-hoc pooled estimate from AI reference reads
> (Claude and a second model family, disagreements settled by a further Claude read). Its samples and reading rules were
> fixed in advance, but pooling them into a rate was not in the plan; the registered primary estimate of this pilot is
> still 10.8% (PROTOCOL.md, Analysis 2). Neither has been checked by people. Outbound text copies the long form in
> SANECITE_SOP.md (facts sheet) and never calls 6.2% "pre-registered".


Pre-registered in PROTOCOL.md (hashes in PREREG_HASHES.txt) before judging; one logged deviation (DEVIATIONS.md:
output caps and spend-guard pacing, prompt and scoring unchanged). Nothing here names a person or paper.

## The finding

In a random sample of 1,600 citations from open-access PubMed Central papers (2015-2025), a three-model AI panel
judged **10.8% to badly misreport the paper they cite** (156 of 1,439 judgeable citations; 95% CI 9.3-12.6%). Human
studies of citations in medicine found 11.9% major errors (Jergas and Baethge, PeerJ 2015, 28 studies). The panel
lands on the same rate, at a cost of about $2.90 per 1,000 citations.

- Citations that credit a specific finding to the cited paper are the riskiest: **15.0% major errors** (93 of 620;
  95% CI 12.4-18.0%), against 8.2% for background citations (49 of 599) and 4.6% for methods and tools (8 of 174).
- Any error, major or minor: 14.7% by the panel (211 of 1,439; 95% CI 12.9-16.6%). The human literature finds 25.4%.
  The blind check below shows why: the panel misses most minor errors.

## Check of the panel (blind second read)

100 random pairs read again by Claude (an Anthropic model, not a person) without seeing the panel's answers:
- Major-error rate: 8.2% for both the panel and the blind read (85 pairs both could judge).
- Of the 7 citations the blind read called major, the panel called 5 major. Of the panel's 9 major calls, the blind read
  agreed on 5, called 1 accurate, 1 minor and 2 "cannot tell".
- Any error: blind read 30.6%, panel 14.1%. Of 25 blind-read minor errors, the panel called 16 accurate. The panel is
  conservative: good at gross misreporting, weak on overstated details.
- Agreement panel vs blind read: 64% on the exact verdict (kappa 0.35); 74% on error vs no error.
A human check of a random subsample comes before any public claim.

## The models disagree, so the panel matters

| Model | Major errors | Any error | Exact quote found | Agrees with blind read |
|---|---|---|---|---|
| Gemma 4 26B | 10.0% | 21.4% | 91% | 72% (kappa 0.44) |
| Nemotron 3 120B | 3.9% | 9.5% | 74% | 63% (kappa 0.17) |
| GPT-OSS 120B | 29.5% | 41.4% | 57% | 54% (kappa 0.24) |

Pairwise agreement 0.59-0.76 (all above the pre-registered 0.5 bar), Fleiss' kappa 0.22, all three identical on
54% of pairs. Single models range from 4% to 30% major errors on the same citations; the majority vote cancels most
of that. Gemma alone is closest to the blind read. Nemotron's answers needed the lenient JSON reader 1,236 times.

## Sample

11,806 random PMC IDs drawn; 1,600 usable pairs (no open full text 4,633; outside 2015-2025 1,762; not a research or
review article 965; no PMID-linked references 2,492; no open cited paper cited in the text 354). Only citations whose
cited paper is itself open access and has a PMID are covered. 3 of the 1,600 cited papers are retracted.

## Cost and time

4,800 model calls, 66 minutes of judging after 42 minutes of sampling. Cloudflare's own usage record for the run's
UTC day: $4.63 (Via Patrum spending was paused all evening).

## Files

data/sample.jsonl, data/judged/*.jsonl, data/results.json, data/blind_compare.json, blind/claude-*.jsonl,
scripts/ (sample, judge, analyze, compare_blind, blind_packets), PROTOCOL.md, DEVIATIONS.md, PREREG_HASHES.txt.
