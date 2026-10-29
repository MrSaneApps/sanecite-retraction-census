# SaneCite stage 3 pilot: are citations accurate? (pre-registered 21 Oct 2026, before any full-run judging)

Owner order, 21 Oct 2026: "do a statistically significant run right now, see how it works." Campaign One checked
citations of retracted papers. This pilot asks the next question from the long-term plan: does a citation say what
the cited paper says? It names no one; results are aggregate only.

## Question

In a random sample of citations in open-access PubMed Central papers (2015-2025), what share does an AI panel judge
to misreport the cited paper (major error), or to misstate a detail (minor error)? And how far do the models agree?

## Sample (scripts/sample.py, seed 20261021)

- Citing papers: PMC IDs drawn uniformly from 1 to 13,683,000; kept if Europe PMC serves open-access full text, the
  paper was published 2015-2025 and it is a research or review article.
- One citation per citing paper (pairs are independent): references with a PMID, seeded shuffle, first whose cited
  paper is open-access full text in Europe PMC and is cited in the body text; one random in-text citation of it.
- The cited paper is shown to the models as title, abstract and the five body paragraphs most similar to the citing
  sentence (BM25).
- Target: 1,600 pairs, so that about 1,500 are judged after failures. At a 25% error rate, n = 1,500 gives a 95%
  margin of about +/- 2.2 points; at 12%, about +/- 1.6.
- Known bias, reported with the results: only citations whose cited paper is open access and indexed by PMID.

## Judging (scripts/judge.py)

- Panel on Cloudflare Workers AI: @cf/openai/gpt-oss-120b, @cf/google/gemma-4-26b-a4b-it,
  @cf/nvidia/nemotron-3-120b-a12b. Settings from the shared harness (llm_bakeoff.cf_profile); research receipt
  20261022T003815Z with a passing smoke for all three.
- Each model gives citation_type (specific_claim, background, method_or_tool, data_source), verdict (accurate,
  minor, major, cannot_tell), a supporting quote and one reason. Prompt text is in judge.py (SYSTEM).
- Up to 3 tries per call. Malformed JSON with all four fields present is read field by field and flagged
  lenient_parse.

## Analysis (fixed now)

1. Panel verdict = the verdict at least 2 of 3 models give; no majority = "split". Same rule for citation_type.
2. **Primary:** share of pairs with a panel verdict of major, among pairs whose panel verdict is accurate, minor or
   major (cannot_tell and split excluded). Wilson 95% interval.
3. **Secondary:** share minor or major on the same base; both shares with cannot_tell and split counted in the base;
   each model's own rates; agreement (pairwise percent agreement and Fleiss' kappa on the four verdicts); rates by
   panel citation_type; share of quotes found verbatim in the excerpts.
4. **Benchmark, not a test:** Jergas and Baethge (PeerJ 2015; 28 studies, medicine, human raters) found 25.4% of
   quotations wrong and 11.9% with major errors. Our sampling and definitions differ, so we report the comparison,
   not a significance test of it.
5. **Check of the panel:** a blind second read of 100 random panel-judged pairs by Claude (an Anthropic model, not a
   person), without seeing the panel's answers. Agreement is reported. It is not a human check; a human check of a
   random subsample comes before any public claim.
6. Cost from the per-call usage (neurons) Cloudflare returns.

## What would change our minds

If the models agree on fewer than half of pairs (pairwise agreement below 0.5 for every pair of models), the panel is
not fit for this task yet and the headline rate is not reported as a finding.
