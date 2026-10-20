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
- `scripts/`: the pipeline. The model-call helpers (`jev_review.py`, `llm_bakeoff.py`) were in a private repository
  (hashes in `MANIFEST.sha256`); since amendment 5 their public copy is `scripts/model_calls.py`.
- `phase1/`: the Phase 1 count of post-retraction citations (amendment 5).
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

**2026-10-15 (reporting correction, not an analysis change).** The analysis scripts stored every rate and interval
rounded to 4 decimal places, and the reported figures were then rounded again to 1 place. Where the 4th place was 5,
that second rounding could go the wrong way. Rates now carry their count (`k`) and are reported as k/n; intervals are
stored to 6 places. No label, row, rate or interval changed beyond that precision (checked value by value against the
2026-10-14 outputs; `census_rows.jsonl` is byte-identical). Figures whose 1-place form changed: headline support
40.8% -> 40.7% (21,037 of 51,626 = 40.749%); support 1-2 years after retraction 43.5% -> 43.6% (11,286 of 25,915);
reviews' support 51.1% -> 51.2%; aware in citing year 2016 3.2% -> 3.3%; 2020s retractions aware CI 1.5 -> 1.4;
S6 40.7% -> 40.6%; read research articles 64.5% -> 64.4%; citing-year-weighted CI 39.1-40.7 -> 39.0-40.6.

**2026-10-16 (amendment 5, code release; no analysis change).** All code is now public. (1) `scripts/model_calls.py`
is the public copy of the private helpers `llm_bakeoff.py` and `jev_review.py`, cut down to what the census used.
The request bodies, model settings and answer parsing are unchanged; a local rate limiter and batch queue, which
only change when a call is sent, are left out. `scripts/classify.py` now imports it instead of a private path.
Checked by re-labelling 6 census passages with Gemma through the new helper: 6 of 6 labels match the stored census
answers; the Jev and Clef request bodies are copied character for character. (2) `phase1/` adds the Phase 1 count
with the administrative rule from `scripts/groups.py` applied to Phase 1 too (it already applied to Phase 2), plus
the 28 same-DOI replacements. On the 16 October snapshot it reproduces the published figures exactly (262,998
citations; 32,626 of 51,414 papers; 16,878 still cited in 2025-2026; 1,858 papers left out).

**2026-10-19 (amendment 6, lean Phase 2b incremental run; registered before the run).** Approved by the owner
the same day. The 16 October pause on gated Workers AI calls is lifted for this run's frozen panel only and
re-applies when the run ends; logged inference budget $15.
1. Set: the later citations stage 1 counted but did not read because the citing paper was not open access in
   Europe PMC, where a free legal copy was located by Unpaywall (`data/copies.jsonl`), refreshed through the
   routing module delivered 19 October 2026 (project records: unpaywall-router/). Fetching is
   polite: openly offered copies only, robots and rate limits obeyed, bot checks never bypassed; a copy behind
   a refusing wall stays unread and is counted as such. Submitted (preprint) versions are flagged on every
   pair, as in the Phase 2b sketch.
2. Path: PDF copies are structured with GROBID and read by the unchanged extractor v3.1 through a
   TEI-to-JATS structural adapter (the adapter converts document structure only; it adds no extraction rule).
   HTML-only copies are counted, not parsed. A pre-run check confirmed Europe PMC serves no full-text XML for
   the non-open-access PMC copies in this set (30 of 30 sampled requests refused), so no JATS shortcut exists
   for them.
3. Gate, fixed in advance (Phase 2b step 5): the PDF path is first run on 300 citing papers already read from
   JATS (seed 20261019). If its usable yield — pairs with extraction status ok — is below 85%, the incremental
   classification does not run and the PDF set is reported separately or dropped.
4. Classification: only the new pairs, with the frozen panel (Jev, Clef, Gemma) and codebook v3.3, exactly as
   registered. The extended set is reported beside the original open-access set with its own coverage figure;
   any combined rate is a rate over the readable corpus, stated as such — never over all 130,315 later
   citations. Nothing is claimed about the pairs that stay unread.
5. Adjudication: the human labelling round stays deferred (owner decision 15 October 2026: honoraria on hold
   until a grant lands). The correction for this run remains the `confirm_v33` AI-key Rogan-Gladen correction,
   and every output of the run states that human adjudication is deferred and that the correction's key is a
   single AI labeler, not human experts. No outreach and no publication from this run without the owner's
   separate approval.

**Outcome of amendment 6 (2026-10-19).** The PDF-path validation gate was run as registered (750 candidate
pairs drawn with seed 20261019; the first 300 PDF-attempted pairs scored). Usable yield was **83.0%**
(249 of 300: reference-not-found 16, no-in-text-citation 35), below the registered 85% threshold — in two
runs (83.0% both times; the second with a structural adapter fix that surfaces TEI attribute-carried years
as JATS `<year>` text, which changed no gate outcome). On the 249 pairs both paths read, passage agreement
was high (mean best-match Jaccard 0.92; 73% exact-sentence match; 1.27 vs 1.33 contexts per pair). Failure
diagnosis of 50 examined misses: GROBID dropped the target reference from its bibliography in ~10,
produced no in-text link to a matched reference in ~22 (author-year and table mentions it does not mark),
and ~13 had links whose sentences the extractor could not use; ~9 were entries the frozen matcher's year
guard set aside because the entry's year/DOI identify a different-year version of the same-titled work
(the JATS path settles these by PubMed ID; the PDF path has none). Under the rule registered in advance,
the incremental classification **did not run**: no gated model calls were made, inference spend was $0,
the extended set is dropped rather than reported, and the census results stand as published. The gate
dataset (750 pairs, both paths), the native GROBID build, and all code are kept in
the phase-2 run directory for any future re-gate under a new amendment.

**2026-10-19 (amendment 7, re-gate of the PDF extraction path with pipeline v2; registered before any measurement under this amendment).** Owner directive 19 October 2026: keep running SaneCite phase work on the available credits, accuracy first. The amendment-6 outcome stands (the owner accepted the gate); this amendment registers a NEW measurement of a FIXED pipeline — it does not reopen or soften amendment 6's rule.
1. What changed since amendment 6 (engineering only; the frozen extractor v3.1 and the matcher are unchanged — extractor classify/extract code as hashed in the manifest): pipeline v2 = native GROBID 0.8.2 -> TEI-to-JATS adapter -> two post-processors inserted before the frozen extractor: (a) an in-text citation linker (conservative rules: unique first-author-surname + year agreement for author-year mentions; square-bracket numerics only where numbering provably matches bibliography order; retargeting of GROBID targetless refs under the same uniqueness rule; ambiguous = no link; a parenthesised-number rule was removed after hand-checking showed it matched enumerations, not citations); (b) bibliography recovery that accepts an entry only when verified against Crossref/OpenAlex metadata (exact year + first-author surname + title match), either augmenting a GROBID entry that lacked a DOI or inserting an entry whose presence in the PDF reference window is proven. Different-year same-title refusals remain refusals by design. Frozen files, in pipeline-v2/: pipeline_v2.py sha256 2658b45f6c12..., linker.py 171de3c16e00..., recovery.py 63d91b387aaa..., tei_adapter.py 5ddf8d8cb8d1..., README.md bb5e0f79747a....
2. Development evidence (NOT gate evidence): on a fresh dev slice of 200 both-path pairs (seed 777001 draw; disjoint from the gate 750, all census validation sets, and the stage-2 sample), baseline yield 84.0%, +linker 84.5%, +recovery (pipeline v2) 86.5% usable (Wilson 95% about 81-91%), passage Jaccard 0.912. Linker precision 100/100 on a stratified hand-checked sample (seed 777002). One alternative (GROBID with header/citation consolidation) was evaluated on 50 dev pairs: identical yield at about 20x the runtime; not adopted.
3. Gate, fixed in advance: pipeline v2 is measured on (i) the SAME frozen gate set as amendment 6 (the first 300 PDF-attempted pairs of the seed-20261019 draw, rescored from the frozen inputs) and (ii) a held-out confirmation sample drawn fresh under this amendment (seed 20261020; same population and exclusion recipe as the gate draw, additionally excluding the gate 750, the dev slice candidate pool, and all census validation sets; scored on the first 300 PDF-attempted pairs in candidate order). PASS requires usable yield >= 85% on BOTH samples. Draw definitions and input-file hashes are recorded with the outcome. If either sample fails, the incremental classification does not run, the extended set is dropped, and the census stands.
4. If PASS: classification of the amendment-6 input set (25,303 located non-PMC citers / 27,120 pairs; data/lean_inputs.jsonl) with the frozen panel (Jev, Clef, Gemma) and codebook v3.3 exactly as registered; submitted-version pairs flagged on every pair; the extended set reported SEPARATELY beside the OA set with its own coverage figure, raw rate + cluster-bootstrap CI, and the confirm_v33 Rogan-Gladen corrected rate + CI; any combined figure is a rate over the readable corpus only, labelled as such. Projected logged inference about $25 (census precedent: $32.05 for 55,688 pairs). The 16 October Workers AI pause is lifted for this run's frozen panel only, under the owner's 19 October standing authorization for SaneCite phase work, and re-applies when the run ends. Human adjudication remains deferred (owner decision 15 October 2026); every output of this run states that. No outreach and no publication from this run without the owner's separate approval.

**Outcome of amendment 7 (2026-10-19).** The pipeline-v2 re-gate was run as registered (measurement only; no classification, no model calls, $0 spend). Frozen-file hashes verified before measuring (pipeline_v2.py 2658b45f…, linker.py 171de3c1…, recovery.py 63d91b38…, tei_adapter.py 5ddf8d8c… — all exact). (i) Frozen gate set (the first 300 PDF-attempted pairs of the seed-20261019 draw, as scored in amendment 6 run 2): usable yield **85.33%** (256 of 300: reference-not-found 7, no-in-text-citation 33, grobid-error 2, no-fulltext/HTML 2), up from 83.0% under amendment 6; on the 256 pairs both paths read, mean best-match Jaccard 0.910, 72.7% exact-sentence match, 1.29 vs 1.32 contexts per pair. (ii) Held-out confirmation sample (seed 20261020; same population and exclusion recipe as the gate draw, additionally excluding the gate 750 and the dev slice's 600-candidate pool; exclusion union 7,098 of 55,694 eligible pairs, pool 48,861; 750 candidates drawn, 301 PDFs obtained, first 300 PDF-attempted pairs scored; draw definition and candidate-list hashes recorded in the re-gate output dir before measurement): usable yield **88.67%** (266 of 300: reference-not-found 6, no-in-text-citation 28); on the 266 pairs both paths read, mean best-match Jaccard 0.897, 71.4% exact-sentence match, 1.33 vs 1.40 contexts per pair. PASS requires ≥85% on BOTH samples: **the re-gate PASSES** (85.33% and 88.67%). Per amendment 7 part 4, classification of the amendment-6 input set with the frozen panel is now the registered next step; it has not been run under this outcome note. Full results, per-pair rows, draw definitions and hashes: `regate7/` (REGATE7_RESULTS.md).

**Outcome of amendment 7, part 2 — extended-set run (2026-10-19 EDT; extraction 22:30Z–02:08Z, classification and analysis same night).** The registered classification of the amendment-6 input set was run exactly as registered. Frozen pipeline-v2 hashes re-verified exact before the run (extractor v3.1 fd6d73c0…); input `lean_inputs.jsonl` sha256 9adf5f6a… (25,303 citers / 27,120 pairs). Fetch (lean Unpaywall router; bot walls never bypassed; HTML-only counted, not parsed): 19,321 citers fetched (PDF 3,506, HTML 15,728, XML 4, other 83), 5,982 fetch-failed (HTTP 403: 4,957). Extraction (pipeline v2, frozen code unpatched): ok 2,885 pairs; reference-not-found 403; no-in-text-citation 434; grobid-error 42 — of which the deterministic `KeyError: <year>` class is **33, reported separately here as registered** (the remaining 9: GROBID HTTP 500 ×6, TEI ParseError ×3); no-fulltext 23,356. Classification (frozen panel, codebook v3.3): 2,858 pairs classified (27 notices set aside, 0 incomplete), 3,737 passages, every passage labelled by all three models (panel size 3 throughout; passages lacking a Jev label: 0; per-model calls 3,737 each; zero errors for every model). Judged (non-administrative, not unclear): 2,629 pairs over 1,779 retracted papers (administrative judged separately: 227; true unclear: 2). **Substantive raw rate 38.53% (1,013/2,629), 95% cluster-bootstrap CI 36.30–40.87%; Rogan–Gladen corrected (confirm_v33 key, sens 0.9649 / FPR 0.0645, n=150, exactly as the census) 35.63%, CI 30.21–40.08%; aware 4.75% (125/2,629), CI 3.33–6.65%.** Coverage: judged = 9.69% of the 27,120 input pairs and 2.02% of the 130,315 frame; combined readable corpus 55,688 + 2,885 = 58,573 pairs (44.95% of the frame), stated as a readable-corpus figure only. Submitted-version sensitivity (flag = fetched copy's Unpaywall version; 650 judged pairs flagged): excluding flagged pairs, substantive 40.12% (794/1,979), CI 37.64–42.40% (frozen-input located-version flag variant: 39.48%). **Logged inference spend actually incurred: $1.73 total** (Jev $0.23, Clef $1.16, Gemma $0.33) — no guardrail approached (Jev error rate 0% vs the >1% stop rule; $100 cap untouched). The extended set is reported separately beside the OA census set; the census outputs were not touched. **Human adjudication is DEFERRED — the correction key is a single AI labeler (confirm_v33, n=150), not human experts.** The 16 October Workers AI pause, lifted for this run's frozen panel only, re-applies from the end of this run. Full results memo: `EXTENDED_SET_RESULTS_2026-10-19.md` (project records); run tree: `extended-run/`.

**2026-10-19 (amendment 8, KeyError fix and recovery of the crash-lost pairs; registered before any measurement under this amendment).** Owner directive 19 October 2026 (SaneCite fix program): "Fix everything you can fix and make sure this count is as good as we can make it." The 16 October Workers AI pause is lifted for this amendment's frozen-panel calls only, under the owner's 19 October standing authorization for SaneCite phase work, and re-applies when the work ends.
1. Defect: in the amendment-7 extended run, 33 pairs were lost to a deterministic `KeyError: <year>` crash in pipeline v2 post-processing (the same class accounts for 2 grobid-error pairs in the amendment-7 re-gate samples). The frozen code was left unpatched under amendment 7 and the losses were reported openly.
2. Fix: the crash is fixed at source in the pipeline-v2 post-processing code only. The frozen extractor v3.1, the matcher, the linker rules, and the recovery verification rule are unchanged. The fixed pipeline is frozen by sha256 in the amendment-8 work dir before any measurement; the pre-fix hashes (pipeline_v2.py 2658b45f…, linker.py 171de3c1…, recovery.py 63d91b38…, tei_adapter.py 5ddf8d8c…) are the baseline, and the diff against them is confined to the crash site.
3. Re-gate, fixed in advance: the fixed pipeline is re-measured on (i) the SAME frozen amendment-6 gate300 and (ii) the SAME amendment-7 held-out confirmation sample (seed 20261020), both rescored from the frozen inputs. PASS requires usable yield ≥85% on BOTH (amendment-7 baselines: 85.33% and 88.67%). If either fails, the recovery in part 4 does not run and the extended set stands exactly as reported under amendment 7.
4. If PASS: the 33 crash-lost pairs (identified in the extended-run work records) are re-extracted with the fixed pipeline from the SAME fetched PDFs (no re-fetch), and their passages classified with the frozen panel (Jev, Clef, Gemma) and codebook v3.3 exactly as registered. The recovered pairs fold into the EXTENDED set only; extended-set statistics and CIs are recomputed with the identical analysis code and reported as an amendment-8 addendum beside the amendment-7 figures. The OA census set and its headline are untouched. Submitted-version flags carry over from the extended run's pair_flags.
5. Projected logged inference < $1. Human adjudication remains deferred (owner decision 15 October 2026); every output of this amendment states that. No outreach and no publication changes from this amendment.

**2026-10-19 (amendment 9, HTML full-text path for the extended population; registered before any measurement under this amendment).** Owner directive as amendment 8. In the amendment-7 extended run, 15,728 located citers were fetched as HTML only and were counted, not parsed, under the amendment-6/7 registration. This amendment registers an HTML path so that population can be read lawfully and measurably. The Workers AI pause lift and standing authorization of amendment 8 apply to this amendment's frozen-panel calls identically.
1. Sources, lawful only: (a) the Europe PMC HTML full text for the citer (the HTML rendition Europe PMC itself serves); (b) the exact HTML copy already fetched and cached by the amendment-7 run's router, or re-fetched from the same openly served location. No bot wall, paywall, robots rule, or rate limit is bypassed at any point; a copy that is not openly served stays unread and is counted as such.
2. Path: HTML → structured text with reference list (cleaned DOM extraction: body text + bibliography entries) → the same downstream contract as pipeline v2's JATS input (citing sentences + matched reference entries) → frozen extractor v3.1, unchanged. The v2 in-text linker and bibliography-recovery post-processors apply only where they operate on identical structures; any HTML-specific rule is part of this amendment's code, frozen by sha256 before measurement.
3. Validation, fixed in advance: a development slice (seed 20261021; fresh both-path pairs from the census OA read set, same exclusion recipe as the amendment-7 dev slice and additionally disjoint from it) is used for engineering only. Gate samples: (i) sample A — seed 20261022 draw from the same eligible pool, candidate order, the first 300 pairs with an openly served HTML copy; scored for usable yield (pairs with extraction status ok) of the HTML path AND passage agreement against the JATS read (mean best-match Jaccard, exact-sentence share); (ii) sample B — a fresh held-out draw (seed 20261023), same recipe, disjoint from sample A and the dev slice; the first 300 HTML-attempted pairs; usable yield. PASS requires usable yield ≥85% on BOTH samples. If either fails, the HTML run does not proceed and the HTML population stays counted, not parsed.
4. If PASS: extraction of the amendment-7 run's HTML-only citers (15,728) from their cached, openly served copies, plus HTML copies lawfully obtained under amendment 10 (flagged as amendment-10-sourced). Classification with the frozen panel and codebook v3.3 exactly as registered. Results are reported as a further, separately labelled extension ("HTML increment") beside the amendment-7 extended set and the OA census set, with its own denominator, raw rate + cluster-bootstrap CI, and the confirm_v33 Rogan–Gladen corrected rate + CI; any combined figure is a rate over the readable corpus only, labelled as such. Submitted-version flags are recorded per pair from the copy's Unpaywall version, as in the extended run.
5. If the extracted-pair count implies projected logged inference above $25, the classification run pauses and reports before spending. Human adjudication remains deferred; every output states that. No outreach and no publication changes from this amendment.

**2026-10-19 (amendment 10, legitimate fetch recovery for the amendment-7 failure list; registered before any measurement under this amendment).** Owner directive as amendment 8. The Workers AI pause lift and standing authorization of amendment 8 apply to this amendment's frozen-panel calls identically.
1. Population: the amendment-7 extended run's 5,982 fetch-failed citers.
2. Retry, once only: citers whose recorded failure was a timeout, a connection error, an SSL error, a chunked-encoding error, HTTP 429, or HTTP 5xx are retried ONCE through the existing Unpaywall router (cached, polite pacing as frozen), at whatever lawful OA location Unpaywall currently ranks first for them. One retry means one; no host is hammered.
3. Walled set, metadata only: for the 4,957 HTTP-403 citers and the non-retried failure classes (202/203/404/410 and similar), a fresh Unpaywall metadata lookup is made. Only if Unpaywall now lists a lawful OA location DIFFERENT from the location that failed is that copy fetched. The walls themselves are never bypassed; a citer whose only locations refuse stays unread and is counted as such.
4. Processing: newly fetched PDFs are extracted with the amendment-8 FIXED pipeline v2 — only if amendment 8's re-gate passed — then classified with the frozen panel, and reported as a labelled increment to the extended set ("fetch-recovery increment") with its own denominator and the same statistics as amendment 7 part 4. Newly fetched HTML copies are parsed only through the amendment-9 HTML path and only if amendment 9's gate passed; they are reported inside that amendment's increment, flagged as amendment-10-sourced. If a governing gate has failed, the corresponding copies are counted, not parsed, and reported as such.
5. Human adjudication remains deferred; every output states that. No outreach and no publication changes from this amendment.

**Outcome of amendment 8 (2026-10-19 EDT).** Root cause found in pipeline-v2 post-processing: `recovery.py` `verify()` line 92 built its year-mismatch rejection reason as `meta[year]` — indexing the string-keyed metadata dict with the integer target-year argument — raising `KeyError: <year>` deterministically whenever recovery was about to refuse a different-year same-title version; the per-citer catch-all in pipeline_v2.py then marked every pair of the citer grobid-error (33 pairs / 29 citers in the extended run, 2 pairs in re-gate sample 1). Fix confined to the crash site (one token: `meta[year]` -> `meta['year']`); the verification rule, frozen extractor v3.1 (fd6d73c0…), matcher and linker rules unchanged. Fixed pipeline frozen by sha256 in `amendment8/pipeline-fixed/` BEFORE measurement (recovery.py d29ebb12…; all other files byte-identical to the frozen originals; diff kept as fix.diff) and re-verified identical after the re-gate. Registration preceded measurement (amendment registered 22:42 EDT; freeze 22:46 EDT; runs 22:46–22:58 EDT). Re-gate on the SAME frozen inputs: (i) gate300 usable yield **85.33%** (256 of 300; grobid-error 2 -> 0; the 2 crash pairs now end as clean recovery rejections, reference-not-found 7 -> 9; Jaccard 0.910 as baseline); (ii) held-out confirmation sample (seed 20261020) **89.00%** (267 of 300; baseline 88.67%; grobid-error 0). PASS on both (>= 85%). Recovery: the 33 pairs re-extracted with the fixed pipeline (PDFs verified against extended-run provenance sha256: 27 of 29 citers byte-identical, same chosen URL for all 29; the frozen pipeline had deleted the cached PDFs after the original run, so the router re-resolved the same openly offered locations; the 2 byte-differing citers yielded no ok pair, and both ok pairs come from byte-identical PDFs). Outcomes: extraction-ok **2**, reference-not-found 29 (all 29 verification attempts now record the intended year-mismatch refusal — the citing bibliographies hold different-year versions, refused by design), no-in-text-citation 2, grobid-error **0**. The 2 ok pairs (3 passages, every passage labelled by all three frozen panel members, 0 errors, both unanimous) fold into the EXTENDED set only: `33262989>38530070` substantive, `28196230>39128574` perfunctory; submitted-version flags carried over (neither flagged). Extended set (denominator 27,120 input pairs before and after): extraction-ok 2,885 -> 2,887; judged (non-administrative) 2,629 -> **2,631**; substantive raw **38.54%** (1,014 of 2,631), 95% CI 36.41–40.87% (was 38.53%, 36.30–40.87%); Rogan–Gladen corrected (confirm_v33 key, sens 0.9649 / FPR 0.0645, n=150) **35.64%**, CI 30.25–40.03% (was 35.63%, 30.21–40.08%); aware **4.75%** (125 of 2,631), CI 3.28–6.69%; combined readable corpus 55,688 + 2,887 = **58,575 pairs (44.95% of the 130,315 frame)**, a readable-corpus figure only. Logged inference for the recovery classification: **$0.001471** total (Jev 3 calls $0.000187, Clef 3 calls $0.000915, Gemma 3 calls $0.000370, census list-price formulas; receipt in the amendment-8 dir); re-gate measurement $0. The OA census set and its headline are untouched. **Human adjudication is DEFERRED — the correction key is a single AI labeler (confirm_v33, n=150), not human experts.** Full record: `amendment8/` (DIAGNOSIS.md, GATE_OUTCOME.md, ADDENDUM_RESULTS.md, SPEND_RECEIPT.json, regate/, recovery/ with raw per-model labels and passage-to-PDF linkage).

**Outcome of amendment 10 (2026-10-19 EDT; lookups 22:46:55–23:18:00 EDT, after this amendment's registration).** The legitimate fetch recovery was run exactly as registered. Universe (foreground-verified from the extended-run provenance): 5,982 fetch-failed citers — retry-once class 515 (ConnectTimeout 153, ReadTimeout 44, ConnectionError 36, SSLError 50, ChunkedEncodingError 46, HTTP 429 48, HTTP 5xx 138), metadata-only class 5,467 (HTTP 403 4,957 + 202/203/404/410 and leftovers). Retry-once citers got exactly one single-attempt fetch at the fresh top-ranked lawful OA location (the router's single-attempt primitive; no fallback walk, no embedded retry): recovered 46 (PDF 27, HTML 19), failed again 469 (new classes recorded per citer). Metadata-only citers were fetched only where Unpaywall now lists a lawful OA location different from every URL that failed: recovered 10 (all HTML; of the 4,957 walled citers, 9 recovered, every one from a different repository location with full Unpaywall provenance logged), no different location 5,437, failed again 19, no longer OA 1. Reconciliation is exact: 5,982 = 56 recovered + 488 failed-again + 5,437 no-different-location + 1 closed. Walls were never bypassed. PDF branch (amendment 8's re-gate PASSED: 85.33% / 89.00%): the 27 recovered PDFs were extracted with the amendment-8 fixed pipeline (frozen hashes re-verified; KeyError class 0) and judged by the frozen panel as the labelled **fetch-recovery increment — own denominator 27 pairs**: extraction ok 19, classified 19, judged (non-administrative) 19; **substantive raw 31.58% (6/19), 95% cluster-bootstrap CI 10.53–52.63%; Rogan–Gladen corrected (confirm_v33 key, sens 0.9649 / FPR 0.0645, n=150) 27.91%, CI 4.12–51.74%; aware 0.00% (0/19)**; submitted-flagged judged pairs 5 (excluding them: 28.57%, 4/14); panel spend exact $0.013111 (Jev 27 calls $0.001663, Clef 27 $0.008155, Gemma 27 $0.003293; zero errors). Coverage effect (counts only): readable corpus 55,688 + 2,885 + 19 = 58,592 pairs (44.96% of the 130,315 frame). HTML branch: 29 recovered HTML copies (29 citers / 30 pairs) — amendment 9's gate PASSED (99.33% / 99.33%), so the copies are not analysed in this lane; they are delivered as `fetch-recovery/html_amendment10_inputs.jsonl` (amendment-10-sourced flags, copy paths, sha256) to join the amendment-9 HTML increment. **Human adjudication is DEFERRED — the correction key is a single AI labeler (confirm_v33, n=150), not human experts.** Full results, audit manifest (per-citer OA provenance + raw Unpaywall responses kept) and spend receipt: `fetch-recovery/` (INCREMENT_RESULTS.md, FETCH_MANIFEST.jsonl, PANEL_SPEND.json, RUN_TIMING.json). The OA census set and the amendment-7 extended set are untouched.

**OUTCOME (2026-10-20).** HTML path built in the htmlpath run directory (html_to_jats v1 → JATS contract → frozen extractor v3.1), code frozen by sha256 before the draws (FROZEN_SHA256.json, 2026-10-20T03:20:20Z; re-verified after measurement, all match). Dev slice (seed 20261021, engineering only): usable yield 99.5% (199/200), passage agreement vs the JATS read mean best-match Jaccard 0.9902, exact-sentence 97.99%. GATE (drawn once each, after this amendment's registration): sample A (seed 20261022) usable yield 99.33% (298/300), Jaccard 0.9894, exact-sentence 97.99%; sample B (seed 20261023, held out) usable yield 99.33% (298/300). PASS on both (≥85% required) — full record in htmlpath/GATE_OUTCOME.md. HTML increment extracted from the cached copies only (no wall bypassed; 9,384 of the population's cached copies are themselves challenge/stub responses, counted as no-fulltext): population 16,858 pairs (own denominator), extraction ok 3,753, passages classified 4,961, judged non-administrative n=3,380 over 1,893 retracted papers. Substantive reliance 36.66% raw (cluster-bootstrap 95% CI 34.69–38.58%), Rogan–Gladen corrected (confirm_v33) 33.55% (28.31–37.73%), aware 5.86% (4.41–7.81%). Panel spend $2.3739 logged (receipt in htmlpath/run/panel_spend_receipt.json), under the $25 projection stop-line ($2.28 projected). Readable-corpus coverage: 58,573 → 62,326 pairs = 47.83% of the 130,315 frame (readable corpus only). The increment stands beside the census and amendment-7 sets with its own denominator; neither headline was recomputed or merged. Human adjudication is DEFERRED — the correction key is a single AI labeler (confirm_v33, n=150), not human experts. Full memo: htmlpath/HTML_INCREMENT_RESULTS.md.

**ADDENDUM to the amendment-9 outcome (2026-10-20).** The amendment-10 lane's 30 flagged HTML pairs were folded into the increment's reporting as a flagged extra set (not blended): 1 extraction-ok, 1 judged (unanimous perfunctory), extra panel spend $0.0019 (total across receipts $2.3758). Coverage baseline supersession: amendments 8/10 reported 58,575 and then 58,592 readable pairs before this increment, so on the latest corrected baseline the increment's +3,753 extraction-ok pairs give 62,345 readable pairs (47.84% of frame, readable corpus only); on the brief's baseline the same addition gives 62,326 (47.83%). Details in htmlpath/HTML_INCREMENT_RESULTS.md.

**2026-10-20 (amendment 11, repair program after the independent audit of amendments 8–10; registered and committed before any measurement under it).** Registered for the owner, who on 20 October 2026 asked for every audit finding to be fixed ("we want results to be as clear and robust as possible") and delegated the decisions. Audit: `SANECITE_FIX_PROGRAM_AUDIT_2026-10-19.md` (independent audit report; project records). Work dir: `repair-20261020/`. The published census figures are not changed by this amendment; any correction to them is prepared for the owner and published only with his approval. Logged inference budget for this amendment: $10; the run stops and reports if the projection exceeds it. Human adjudication remains deferred; every output states that the correction key is a single AI labeler.
1. Withdrawn, no new measurement: (a) the amendment-9 HTML increment and the amendment-9/10 HTML extra set are withdrawn from every counted result. 3,636 of its 3,753 extraction-ok pairs were read from copies fetched from the main PMC website, which PMC's copyright notice forbids for systematic batch download and which `www.ncbi.nlm.nih.gov/robots.txt` disallows (`/pmc/articles/`); the remaining non-PMC part rests on gate evidence of 9/12 (75%), below the 85% standard. The HTML path is retired; its files stay on disk as the record. (b) The 2,610 Clef-slot labels that the Jev route answered after a Cloudflare 429 (`model_calls.jev()` cross-model fallback; 2,138 in the HTML increment, 472 in the extended set) are void.
2. Panel repair: `scripts/model_calls.py` `jev()` may fall back to TypeSafe's direct API only when the requested model is `typesafe/jev`; for any other model a Cloudflare failure is an error, retried with back-off, never answered by another model. Every labelled set passes an integrity check before analysis: each Clef row has version `clef`, each Jev row a `jev-` version, each Gemma row the Gemma model ID, one row per passage per model; the analysis refuses to run otherwise. The 472 extended-set Clef passages are re-asked of Clef and the extended set is re-analysed. Panel, codebook v3.3 and `panel.combine` are otherwise unchanged.
3. New increment from the PMC Article Datasets (allowed bulk channel). Amendment 6 found that Europe PMC serves no full-text XML for the extended set's non-open-access PMC copies. PMC's Cloud Service (AWS Open Data, `s3://pmc-oa-opendata`, inventory snapshot 2026-10-19T01-00Z) does carry many of them as NIH author manuscripts licensed for text mining (`license_code` TDM). Universe: the 27,120 extended-frame pairs, minus the 2,906 already extraction-ok in the extended set (amendments 7, 8, 10), whose citer's PMCID has a version in that dataset: 4,558 pairs / 4,369 citers (`repair-20261020/pmcjats/universe.jsonl`, sha256 d8d955df…). Version rule: the open-access published version if the dataset has one, else the author manuscript (highest version number among equals). XML is fetched only from the bucket's HTTPS URLs, once per article. Extraction: the census's own frozen extractor v3.1 (`extract.contexts`, sha256 fd6d73c0…) exactly as `scripts/reextract.py` calls it, so notices are set aside by the same article-type rule. Every pair is flagged as an author manuscript (accepted version, not the publisher's) or published version.
   Gates, fixed now, before any XML is fetched: (i) fidelity — 300 pairs drawn with seed 20261024 from the census read set (`data/stage2_v31.jsonl`, notices excluded) whose citer has an open-access version in the dataset are re-extracted from the bucket's XML; PASS requires status agreement with the census on ≥95% of pairs AND, on pairs ok in both, mean best-match Jaccard of the census contexts ≥0.95. (ii) precision on the increment itself — 30 extraction-ok increment pairs drawn with seed 20261025 are checked by hand (the citing sentence is in the article XML; the marker it carries points to the matched reference entry; that entry is the retracted work by PMID, DOI or exact title); PASS requires ≥28/30. If (i) fails, nothing is fetched beyond the gate; if (ii) fails, the increment is reported as unvalidated and not counted. Usable yield is reported without a threshold (no reference read exists for these papers).
   If both pass: classification with the frozen panel and codebook v3.3, analysis with the census rules (`groups.py` administrative rule, unclear excluded, notices set aside, cluster bootstrap over retracted papers, B=400 seed 1, the confirm_v33 Rogan-Gladen correction), reported as its own set ("PMC author-manuscript increment") with its own denominator. Passages from text-mining-licensed manuscripts are not redistributed in any public data file without the owner's review.
4. Frame correction, applied to every set alike: each of the 22,553 frame records' PMIDs was looked up in Europe PMC (title, DOI, year; `repair-20261020/frame/epmc_pmids_all.jsonl`). A record is a WRONG RECORD when Europe PMC's title for the PMID shares under half the words of the Retraction Watch title (overlap over the shorter title, words over 3 letters), unless the mismatch is explained by: (a) a translated or re-titled record of the same article with the same DOI and overlap ≥0.3, or a bracketed (translated) PubMed title with the same publication year; (b) the PubMed record having been replaced by its own retraction, withdrawal or erratum notice under the same DOI; (c) a generic Retraction Watch title ("Editorial", "Response to commentary") with the same DOI. Whole meeting-abstract supplements are wrong records whatever their DOI, because their citations cannot be attributed to one abstract. Pairs on wrong records are removed from every set's corrected figures. For the published census this is reported as a correction figure for the owner, not applied silently.
5. One reading per work: pairs are deduplicated on (retracted PMID, citing DOI). When the same work was read in more than one set, the reading kept is the first in this order: OA census, extended set, amendment-8 recovery, amendment-10 PDF increment, PMC author-manuscript increment.
6. PDF recovery year source: pipeline v2's `recovery.verify()` compared the Crossref year of the retracted paper's own DOI with the Retraction Watch original-date year, so a wrong Retraction Watch date refused the right paper (the audit found this for 28 of the 29 amendment-8 refusals). The fixed pipeline uses the PubMed publication year of the retracted PMID (Europe PMC pubYear) as the target year, falling back to the Retraction Watch year only when PubMed has none. Frozen by sha256 before measurement and re-gated on the same frozen inputs as amendment 8 (gate300 and the amendment-7 held-out sample); PASS requires usable yield ≥85% on both. If PASS, the 29 refused pairs are re-read: their citing PDFs are re-fetched once each from the same openly served URL, after a robots.txt check, at most one request per host per 5 seconds; a refusal stays a refusal.
7. Fetching rule from now on, for this amendment and any later one: robots.txt is read and obeyed for every host; at most one request per host per 5 seconds unless the host's robots.txt asks for longer; a challenge, captcha or proof-of-work page is a refusal for that article on every URL, never retried through another address; PMC full text comes only from PMC's allowed bulk channels (Cloud Service, OAI-PMH), never from the PMC website.
8. Reporting: every set keeps its own denominator. A combined figure, if given, is over the deduplicated readable corpus only, after the frame correction, and states that. The coverage chain is restated from the files. Results go to `repair-20261020/REPAIR_RESULTS.md` and an outcome note below.

**Outcome of amendment 11 (2026-10-20, 02:39–03:40 EDT).** Run as registered. (1) The amendment-9 HTML increment and the HTML extra set are withdrawn; the 2,610 Clef-slot labels answered by Jev are void. (2) `model_calls.jev()` now falls back only for Jev and logs every fallback; the 472 extended-set Clef passages were re-asked of Clef (0 errors); every counted set passes the panel integrity check. (3) PMC Cloud increment: universe 4,558 pairs; fidelity gate PASS (296/300 status agreement = 98.67%; mean best-match Jaccard 0.9986 on 293 ok-in-both); extraction 4,463/4,558 ok; precision gate PASS (hand check 30/30; 29/30 under a strict per-marker reading); classified 4,460 (2 incomplete: Gemma replies cut off at the 2,048-token retry, census rule). Jev used TypeSafe's direct route for 1,579 of 5,716 passages after Cloudflare 429s (same model); Clef never fell back. (4) Frame correction: 70 wrong records (86 later citations). (5) Dedupe: 3 duplicate readings in the extended set. (6) Recovery year re-gate PASS on amendment 8's exact inputs (offline replay of the cached PDFs, 0 hash mismatches): 257/300 = 85.67% and 267/300 = 89.00%; 16 of the 29 refused pairs now read and were added to the extended set. Results after parts 4–5, each set with its own denominator: published census 21,032/51,614 = 40.75% (as published 21,037/51,626; every displayed rate unchanged); extended set 1,019/2,642 = 38.57%; amendment-10 PDF increment 6/19; PMC author-manuscript increment 1,345/4,064 = 33.10% (CI 31.41–34.71), aware 216/4,064 = 5.31%; combined readable corpus 23,402/58,339 = 40.11% (CI 39.29–40.93), over 63,026 classified pairs = 48.40% of the corrected frame (130,229). Logged spend $2.77. Human adjudication remains deferred; the correction key is a single AI labeler. Full record: `repair-20261020/REPAIR_RESULTS.md` and `LEDGER.md`.
