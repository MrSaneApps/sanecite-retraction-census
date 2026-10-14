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

## Amendments (each dated; none made after seeing final results)

**2026-10-13 ~23:55Z**, before the final analysis:
1. `codebook.md` in the first commit was a stale v2 explainer copied from the website. The rules actually used are
   those in `scripts/classify.py` (codebook v3.3, hashed in the first commit). `codebook.md` is now generated from
   that file. No rule changed.
2. `analyze_census.py`: adds the confidence interval for the corrected rate promised above (resamples the confirmation
   set; observed rate drawn from its census bootstrap interval). No other change.
3. New scripts for the planned analyses: `coverage_types.py` (analyses 4 and 5), `hs_compare.py` (analysis 6),
   `human_packet.py` (draws the human labelling set: seed 2027, 200 citing papers, 254 passages, excluding all 771
   pairs used before; list in `human_labels/draw.json`, instructions in `human_labels/INSTRUCTIONS.md`).
4. `hs_compare.py` was run once on incomplete labels (Gemma about 40% done) to test it. Hsiao and Schneider's data
   (Illinois Data Bank IDB-3213475, v2) gives, on 8,944 shared citing pairs: agreement of our *aware* label with their
   hand-checked acknowledgement 97.7%, kappa 0.74. The final figure will be reported from complete labels.

**2026-10-14 ~02:45Z (amendment 2)**, before the final analysis:
1. Robustness analyses (`scripts/sensitivity.py`), primary outcome recomputed with: S1 citing papers that are themselves
   retracted removed; S2 only citations two or more years after retraction; S3 only pairs whose every passage the three
   models labelled unanimously; S4 first passage only (the main rule takes the strongest of up to three); S5 only
   references matched by PubMed ID or DOI. Also Fleiss' kappa across the three models (passage level).
2. Self-citation (exploratory): a shared author (surname and first initial) between the retracted and citing paper;
   rates reported for self and other citations.
3. Test-retest (`scripts/retest.py`): every panel model re-asked about 500 random census passages (seed 99); share of
   identical labels per model and for the panel.
4. Gemma replies cut off at the default length (9 passages at the time of writing) are retried once with a larger
   reply cap (`SANECITE_MAX_TOKENS`, the only change to `classify.py`). Passages still without a Gemma label are
   decided by Jev and Clef, with Clef breaking ties, and counted.
5. Reference-match audit (done): 89% of read pairs were matched by PubMed ID or DOI. Of title matches, 97.2% (5,375 of
   5,530) carry the retracted paper's first-author surname; reading 12 of the other 155 showed mostly name-format
   differences, plus Cochrane reviews whose later versions share the title (administrative, outside the headline).
6. Disclosure of interim looks: `sensitivity.py` was run once on partial labels (Gemma about 85% done) to test it.
   Partial results: primary 38.5%; S1 38.5%; S2 37.3%; S3 35.8%; S4 34.1%; S5 38.7%; Fleiss kappa 0.81 (label).
   No rule changed after this run.
7. AI use: the labels are produced by language models; Claude (Anthropic) wrote most of the code, produced the
   development and validation reference labels, and drafted text. A human check is planned (Validation).

**2026-10-14 ~04:15Z (amendment 3), after the final analysis.** An internal review (four checks run by Claude
subagents: a recompute of every figure from the raw labels, a code review, a blind re-reading of 110 census pairs, and
a literature check) found the items below. No labelling rule, model output or label changed, and the headline rate is
unchanged (40.75%).
1. Grouping errors fixed in a shared `scripts/groups.py` (used by `analyze_census.py` and `coverage_types.py`). The
   misconduct pattern missed Retraction Watch tags it was meant to catch (compromised peer review, computer-aided or
   computer-generated content, rogue editor, hoax, salami slicing, taken via peer review, sabotage), which fell into
   "other or unstated"; the words of administrative tags could leak into the misconduct and error patterns; "updated to
   retraction", "updated to correction" and "no further action" are now process tags, which moves 10 citations into the
   administrative group (headline n 51,636 -> 51,626). Field was the alphabetically first subject code; it is now the
   set of codes (basic life sciences only, health sciences only, both, other).
2. Promised analyses the code did not run, now run: read vs unread citations by retraction reason and field (analysis
   4; `coverage_types.py`, which also now leaves unread administrative papers out of the year weights); the aware rate
   over Hsiao and Schneider's citing years, to 2019 (analysis 6). Passages without a Jev label: 0.
3. Deviation disclosed: amendment 2 item 4 said passages still without a Gemma label would be decided by Jev and Clef
   and counted. `analyze_census.py` set the 6 affected pairs (9 passages) aside instead. Jev and Clef agree on all 9;
   counting them leaves the rate at 40.75%. When a Clef call failed, the model helper silently answered with Jev for 7
   passages; all 7 are unanimous. Gemma rows carry no model version, and per-call dates are in the run logs, not the
   rows.
4. Exploratory additions: model agreement on the raw use answer and on passages where the work is cited alone; a
   two-way cluster bootstrap (retracted and citing paper); timing by the citing paper's JATS received date (S6), also
   for the synthesis inclusions; where the word "retract" sits in flagged reference entries; the corrected rate with the
   confirmation set limited to non-administrative pairs (37.0%), and rescoring of that set from its saved labels
   (reproduces 142/150); papers with two or more substantive citations; the aware rate when the reference list says
   retracted. `paper_numbers.py` generates every figure the paper quotes. `holdout_v31.py` (draw and score of the blind
   sets) and the confirmation set's passages and model labels are now posted.
5. Exploratory synthesis check (571 pairs labelled as counted in a meta-analysis, systematic review or guideline,
   re-read by Claude at passage level; 507 confirmed) is reported in the paper as exploratory.
6. Wording: the paper calls the substantive label "cited as support" rather than "relied on", because the blind
   re-reading found that it also covers method credits and statements of agreement.
7. Data release: `data/` now holds the census data (frame, extracted passages, each model's labels, citing-paper
   metadata, pair labels), the result files, `paper_numbers.md` and the synthesis check, gzipped where large. All
   figures are provisional until the human labelling round above.

**2026-10-14 ~13:45Z (amendment 4)**, before any human answer exists (no labeller has been recruited yet):
1. Scoring of the human round is fixed now in `scripts/human_score.py`. Each labeller's two answers per passage go
   through `classify.label()` with the citation-group count from `citegroup.py`, exactly as the models' answers do; a
   citing paper's label is the strongest across its passages, and a paper counts only when all its passages are
   answered. Tested by filling the sheets with Jev's and Gemma's own answers: all 254 passage labels match the labels
   stored in the census for both models.
2. "Panel-human agreement" in the Validation rule means agreement on the four-way citing-paper label between the panel
   and each labeller, computed separately. The rule is triggered if agreement with EITHER labeller is below 85%. We
   also report Cohen's kappa between the two labellers, the panel's agreement with the papers both labellers label the
   same, and agreement on the headline question alone (substantive or not).
3. If the rule is triggered, the corrected headline uses the same Rogan-Gladen method as the confirmation set, with
   sensitivity and false-positive rate taken from the panel against the papers both labellers agree on.
4. The Validation section also promised agreement "with the Claude labels". No Claude labels exist for this draw, and
   adding them would add another AI reader, not a human check, so that comparison is dropped.
5. Labellers work in an Excel workbook built by `scripts/human_sheets.py` from `passages.csv`: same passages, same
   order, drop-down answers, no model label shown.
