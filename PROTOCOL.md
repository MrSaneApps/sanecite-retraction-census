# SaneCite retraction census: analysis protocol

Registered 13 October 2026, before the final census analysis was run.
Project: SaneCite (sanecite.com), an open checker of the scientific record. Contact: hi@saneapps.com.

## What is fixed here

The pipeline that reads every citation (extractor v3.1, codebook v3.3, three-model panel), the outcomes, and every
analysis below. `MANIFEST.sha256` gives the SHA-256 of each script and of the data files that existed when this was
written. Anything reported later that is not listed here will be labelled exploratory.

## Honest status at registration

- Stage 1 (finding citations) and stage 2 (extracting citing sentences) are complete.
- Stage 3 (classification): Jev and Clef have labelled all 72,139 citing passages; Gemma is about a third done.
- Interim looks: while building the pipeline, the analysis code was run on partial data (about 11,700 citing papers
  with all three labels) to test it, and an earlier data-page build showed partial numbers. No rule was changed after
  those runs. The final analysis on complete data has not been run.
- Jev ran out of paid credit after 44,248 passages; the run was paused and resumed with the same model after a top-up.
  No passage was judged by a different panel.
- The two validation answer keys (below) were labelled by Claude (Anthropic), a language model, blind to the panel's
  output. They are not human labels. A human labelling round is planned (see Validation).

## Frame and data

- Frame: every Retraction Watch record (via Crossref, downloaded 13 October 2026) with RetractionNature = Retraction,
  an original-paper PubMed ID, retracted 1990-2023; deduplicated by PubMed ID: 22,553 retracted papers. A census,
  not a sample.
- Later citations: Europe PMC papers citing the retracted paper and published in a calendar year after the retraction
  year (`CITES:<pmid>_MED AND PUB_YEAR:[ry+1 TO 2026]`). 16,019 papers were cited after retraction; 130,315 later
  citations; 58,358 have open-access full text and were read.
- Extraction, codebook and panel: as in `codebook.md` and the scripts. Retraction notices, corrections and expressions
  of concern that cite the paper are set aside.

## Labels

Per citing passage: *aware* (the text disputes the work), *substantive* (the work is counted as data in a review, or
it is the only reference in its group and the sentence rests on its finding), *perfunctory* (everything else), or
*unclear*. Panel = majority of Jev (typesafe/jev), Clef (@cf/cloudflare/clef) and Gemma 4 26B
(@cf/google/gemma-4-26b-a4b-it); *aware* if any model says disputed and the passage has a retraction, fraud or
image-integrity word, or if two models say disputed. A citing paper's label is the strongest across its passages
(up to three). If a passage lacks a Jev label, Gemma + Clef decide and Clef breaks ties; the number of such passages
will be reported (expected: none).

## Primary outcome

Share of judged citing papers (label not *unclear*) that rely substantively on the retracted work, among retractions
that are not administrative. Administrative = Retraction Watch reasons that find no fault in the science (withdrawn
as out of date, retract and replace, withdrawn to publish elsewhere, publisher's duplicate or error, temporary
removal); reported separately.

Reported as: (a) the raw panel rate with a 95% cluster bootstrap CI over retracted papers (B = 400);
(b) the rate corrected for measured misclassification (Rogan-Gladen, sensitivity and false-positive rate from the
confirmation set below), with a CI that also resamples the confirmation set; (c) a strict and lenient band for
passages where the models disagreed.

## Secondary outcomes

1. Share of judged citing papers that are *aware* (acknowledge or dispute the retraction).
2. Primary and *aware* rates by retraction reason group, field (Retraction Watch subject), years since retraction,
   retraction year, and whether the citing paper's reference entry itself says "retracted".
3. Share of retracted papers with at least one substantive later citation.

## Planned additional analyses

4. **Open-access coverage.** For every later citation (read or not), Europe PMC metadata: year, journal, publication
   type, open-access flag (`scripts/citer_meta.py`). Compare read and unread citers by citing year, retraction reason,
   field and publication type. Re-weight the primary rate so each retracted paper counts by its total later citations
   (not only the ones we could read), and by citing year. Report both.
5. **Where reliance lands.** Primary and *aware* rates by citing-paper type from Europe PMC publication types:
   review, systematic review, meta-analysis, practice guideline / guideline, randomised controlled trial / clinical
   trial, research article, other. Counts of substantive citations in each.
6. **Comparison with Hsiao and Schneider (QSS 2021).** Their measure was whether the citing text acknowledges the
   retraction. We report our *aware* rate on the matching window (retracted papers in PubMed, citing papers in the PMC
   open-access subset, citing years up to the end of their data), and, if their list of papers is public, on the papers
   both studies cover.

## Validation

- Development: 321 citing papers (130 fresh + 191 from the pilot), labelled by Claude.
- Holdout (seed 31337, 300 citing papers, labelled blind before any model output was read): frozen v3.1 panel
  277/300 = 92.3% (Wilson 88.8-94.8). Its errors led to v3.3, so this set is no longer clean for v3.3.
- Confirmation (seed 4242, 150 fresh citing papers, no overlap, labelled blind): frozen v3.3 panel 142/150 = 94.7%
  (89.8-97.3); all-three-agree 123/126 = 97.6%. This set supplies the misclassification correction.
- Planned: two people with biomedical training label about 200 citing papers blind (drawn at random from the census,
  excluding the sets above). We will report their agreement with each other (Cohen's kappa) and with the panel and with
  the Claude labels. If panel-human agreement falls below 85%, the headline will be reported with that agreement and a
  correction based on the human labels.

## Limitations stated in advance

Only PubMed-indexed retractions; only open-access full text is read (45% of later citations); citations in the
retraction year are not counted (lower bound); up to three passages per citing paper; model labels can drift if a
hosted model is updated (versions and dates are logged per call).

## Files

- `codebook.md`: the questions and rules the models answer.
- `scripts/`: the pipeline. The model-call helpers (`jev_review.py`, `llm_bakeoff.py`) are in a private repository;
  their hashes are in `MANIFEST.sha256`.
- `validation/`: holdout and confirmation answer keys and scores.
