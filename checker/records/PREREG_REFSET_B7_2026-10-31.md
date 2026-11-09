# Pre-registration: batch 7 answer key (AI reference set), written 30 Oct 2026, revised and registered 31 Oct 2026

**Status: REGISTERED 31 Oct 2026, before any batch 7 sampling or reading; sha256 in `PREREG_HASHES.txt`, committed to the public census repo. Registered two days earlier than RUN_PLAN.md's Mon 2 Nov (owner, 31 Oct: keep working while credit is available); no rule changed for it.** Owner decisions, 30 Oct 2026, 8:50 PM
ET (RUN_PLAN.md): design as drafted with Part B internal (option a); the sha256 posted as a commit to the public
census repo before sampling; and the Claude reads on the Anthropic API credit (Message Batches) instead of separate Claude
sessions. Revised 31 Oct for the API route after the calibration in `CALIB_OPUS_API_2026-10-31.md`. Registration:
copy this file to `outputs/sanecite-stage3-pilot-20261021/PREREG_REFSET_B7_<date>.md`, put its sha256 and the
sha256 of every new or changed script in `PREREG_HASHES.txt`, and commit that hash file to the public census repo,
all before any sampling or reading. Run plan: `RUN_PLAN.md`. Changes from the first
draft and why: `REVIEW_LOG.md` (same folder).

Figures quoted here come from the stage 3 result files in the working folder (B6_RESULT_2026-10-22.md, TUNING_RESULTS,
PREREG_SYSTEM), batch 6 data files, `census_rows.jsonl.gz`, the Lists build and the facts.json `stage3`, `census_p2`
and `lists` blocks. They are internal planning inputs. Nothing in this draft is outbound text.

## 1. Why

- The 150-pair references used for tuning held only 5 to 13 major errors each. Kappa for major errors swung widely
  between batches, and three fresh tests showed that tuning on sets this small overfits (TUNING_RESULTS).
- Batch 6 (996 drawn, 915 judged, 66 major) fixed part of this. Its major rate is 7.2% (95% CI 5.7-9.1%), and the two
  reference readers agreed with each other at kappa_major 0.658. Sixty-six majors is still a thin base for scoring new
  candidate systems, for subgroup claims (the site's "specific findings are riskiest" line is marked "not in the
  test's plan"), and for drawing a human check that needs enough majors to estimate how often an AI "major" is right.
- The census correction (Rogan-Gladen) rests on one 150-item key read by one AI labeller (confirm_v33, Claude Opus
  5.5). Errors in the census panel cluster where its three models disagree. No key has looked there on purpose.
- Goal: a bigger, fresh AI answer key, read on the Max plan's API credit (expires 25 Nov 2026), and one scored
  confirmation of the frozen checker setup (`FROZEN_SETUP_2026-10-30.md`, chosen on batches 2-6 with Cloudflare
  off). It is an AI reference. It does not replace the human check; it sets that check up (section 9).

## 2. Two parts, reported separately

| Part | Task | Sample | Size | Status |
|---|---|---|---|---|
| A | Citation accuracy (stage 3: does the citation say what the cited paper says?) | Simple random, fresh | 1,320 pairs | Primary. Registered under stage 3. Gives the rate estimates. |
| B | Census label (codebook v3.3: aware / cited as support / mentioned in passing) | Targeted strata | 440 pairs | Internal and exploratory (see below). Never pooled into Part A. |

**Part B is internal and exploratory.** It is not a census protocol amendment. It changes no census figure, no census
error note and no Rogan-Gladen correction, whatever it finds. At most it tells the owner where a later, registered
census amendment and a human check should look. IMPROVEMENT_PLAN says the targeted stratum (item 5) and the canary
(item 2) need a registered amendment in the public census repo before they are used for the census; registering
that publishes it, so it waits for the owner. If the owner chooses instead to register Part B as a census amendment
(decision 1, option b), the census repo amendment is drafted separately and goes through the census registration
rules; this draft's Part B rules then become that amendment's text and section 8's Part B rows change with it.
Note: item 5 was planned as a human check ("runs when reviewers are paid"). Part B uses the same strata for an AI
key now. The human check of those strata is still to come; Part B's sheets are built in the human packet format
so that check can reuse them.

Why the targeted strata sit in the census, not in Part A: a "panel disagreement" stratum needs panel output on fresh
citations. For the accuracy task that means running the locked checker (Clef, DeepSeek, Qwen, GLM), which runs on
Cloudflare Workers AI, which is off. The census already has three-model labels on every pair and the Lists
already name their counted citations, so the targeted strata cost no model calls to draw.

## 3. Sampling

### Part A: random sample (seed 7007)
- `scripts/sample_v2.py OUT.jsonl 1330 --seed 7007`, unchanged, with `MAX_PMCID = 13_683_000` as in batch 6 so the
  population is the same (PMC open-access research and review articles, 2015-2025, one pair per citing paper).
- `b7/filter_seen.py` (new) drops every pair whose citing PMCID appears in batches 1-6 (same rule as batch 6) and
  keeps pairs with status "ok". It writes exactly the first 1,320 remaining ok rows by draw order to
  `b7/sample_read.jsonl`, or all of them if fewer remain. The run goes ahead if at least 1,210 remain (expected
  judged about 1,110, so the 1,000 bar still holds).
- Every row of `b7/sample_read.jsonl` is read by every reader; there are no reading packets and no packet cut
  (the API route removed the weekly-meter limit that made a cut necessary).
- Pre-registered subgroups (Part A only): citation_type (specific_claim, background, method_or_tool, data_source)
  as called by the adjudicated key.

### Part B: targeted strata (census codebook v3.3)
Base: the census headline base only, that is the judged pairs in `protocol/data/census_rows.jsonl.gz`. Dropped before
any draw: administrative retractions (reason "administrative (no fault found in the science)", 4,044 pairs), the 18
"unclear" pairs, and the 12 wrong_record pairs (the same 12 the 20 Oct fix removed; read_fix = 55,676). That leaves
51,614 pairs: 8,063 panel disagreements (route majority 8,050 + split 13) and 43,551 unanimous. Passages come from
`protocol/data/stage2_v31.jsonl`, notices left out. Then excluded: every pair in confirm_v33, holdout_v31, any
`*gold*.json`, and the human packet draw (`human_packet.py`, seed 2027), so the human random 200 stays untouched and
every key stays independent. `census_key_draw.py` prints the pool sizes after these exclusions before it draws.

| Stratum | Pool (30 Oct 2026, before the key/human exclusions) | Draw | Seed | Rule |
|---|---|---|---|---|
| B2 Lists citations | Every citation counted toward a **published** entry in the current Lists build on the site's main branch (`websites/sanecite.com/lists/*.csv`; the lists worktree was merged into main by 30 Oct; facts `lists` block, 30 Oct 2026: 9 papers, 10 + 10 journals, 13 authors), deduped by pair_id. Eligible pools on 31 Oct (commit 3677e76, after the key and human exclusions): 138 author, 4,217 journal, 451 paper citations | 132 | 7102 | 44 each from the author, journal and paper Lists; a pair on two Lists counts once, under the first List it is drawn for |
| B1 Panel disagreements | 8,063 judged pairs with route majority or split | 176 | 7101 | Half from pairs the panel called "cited as support", half from the rest; B2 pairs removed first |
| B3 Unanimous | 43,551 judged pairs with route unanimous | 132 | 7103 | Simple random; B2 pairs removed first |

B2 build gate: `census_key_draw.py` reads the Lists build from a `git archive` snapshot of the site at the commit
current when the draw runs (recorded in `draw_log.json`; stored on SaneBulk), by importing that snapshot's
`tools/lists.py`, so `list_corrections.json` exclusions and relabels apply exactly as the build applies them. (Importing
it in the live repo would rewrite `tools/reach_citers.json`, which is why a snapshot is used.) Before it draws, its
count for every published entry must equal the published column (`cited_as_support` for papers and journals,
`citations_confirmed` for authors). If any entry does not match, B2 is not drawn and the miss is logged; B1 and B3 go
ahead. Dry run 31 Oct at 3677e76: all 9 paper, 20 journal and 13 author counts match. Each B2 pair is tagged with
where its List label came from: `full_read` (its paper is in the full-read set, or the pair was relabelled after a
full-text check), `second_reading` (author counts, which rest on the second reading) or `census` (the census
label, most journal citations). B2 results are reported by tag.

Draw order: B2, then B1, then B3, so no pair is in two strata. Order: strata mixed in one random order (seed 7104)
so readers cannot tell the stratum, written as `partb_records.jsonl` with no stratum field (11-pair "packet" numbers
kept for reference only). Every passage of every pair is read.
Draw script (new, hashed before use): `census_key_draw.py`. It writes the same `draw.json` and `passages.csv` format
as `protocol/scripts/human_packet.py`, one set per stratum, so `human_score.py` scores it unchanged and the later
human check can reuse the same sheets.

### Canary (drift check, not part of either result)
- Pool: batch 6 gold items that a Claude reader finished, that is gold draws present in `batches/b6/ref_claude/
  ref-*.jsonl`, minus the 66 Claude-stop draws (`grok_draws_all.json`), minus the 11 draws of `adj/adj-14.md` (an
  adjudication packet Claude stopped on; 3 of them are also stop draws), minus "cannot_tell" gold items. Pool on
  30 Oct: 848 items (681 accurate, 110 minor, 57 major). No canary item was ever in a packet Claude stopped on, so
  re-reading it is not the retry C8.3 forbids.
- Draw: 33 items, seed 7201, from the 848 sorted by draw number (`b7/canary_draw.py`, drawn 31 Oct before any
  batch 7 read; the calibration set was drawn from the rest of the pool). All 33 are read by reader 1, with the same
  settings, in the same Message Batch as the Part A first reads, under their own batch label. Canary items never
  enter batch 7.
- Stop rule: fewer than 27 of 33 matching batch 6 gold pauses the run until the cause is found and logged.
- Pooling tolerance (used in section 7, item 5): at least 28 of 33 canary items match batch 6 gold.
  Reference: batch 6's own Claude reads match gold on 96.0% of this pool (814 of 848), but that is inflated, because
  gold was built from agreement with Claude. If a fresh Claude reader repeats at 90%, it passes 28 of 33 about 89% of
  the time; at 85%, about 63%.

## 4. Readers

All readers are blind: they see the item and the rules only, never another reader's verdict, any panel or system
output, any census label or any Lists reading.

### Reader model record
Batch 6 recorded no Claude model id: `ref_claude/ref-*.jsonl` rows hold only draw, citation_type, verdict and reason,
and READING_RULES, ADJ_RULES, PREREG_SYSTEM and B6_RESULT name no Claude model. So "the same reader as batch 6"
cannot be checked. Batch 7 therefore:
- registers the Claude reader exactly: model `claude-opus-5-5` on the Anthropic Message Batches API (API version
  2026-10-21, Python SDK anthropic 2.3.0), one request per item, `output_config.effort` "medium" for first reads
  and the canary, "high" for adjudication, JSON through `output_config.format`, max_tokens 8000. The effort was
  fixed by the calibration on 164 batch 6 items (`CALIB_OPUS_API_2026-10-31.md`: medium exact 87.6% and
  kappa_major 0.823 against batch 6 gold, within its pre-set margin of high's 89.4% and 0.837). Adjudication uses
  high because it is the third careful read; high scored best in the calibration;
- records the model id per row (`scripts/anthropic_read.py` writes it; `b7/api_to_ref.py` carries it into the
  reader-A rows);
- uses the canary result and its tolerance (section 3) as the test of whether batch 6 (separate Claude sessions) and batch 7 (API)
  readers can be pooled.

### Part A
| Role | Reader | Evidence for the choice |
|---|---|---|
| Reader 1 | Claude Opus 5.5 on the API, settings above. System prompt = `judge_v2.SYSTEM`, the v2 rules (the text of batch 6 `READING_RULES.md` above its "HOW TO WORK" block, which only told a Claude session how to handle files); user message = `judge_v2.user_msg` (the item as in the batch 6 packets). `scripts/anthropic_read.py submit claude-opus-5-5 medium b7 --sample b7/sample_read.jsonl`; `b7/api_to_ref.py` writes `b7/ref_claude/ref-api.jsonl` | Reader 1 for batches 2-6 was Claude (separate sessions, model unrecorded in batch 6); calibration above |
| Reader 2 | Muse via `judge_v2.py --models muse --prompt v2`, unchanged | Reader B for batches 2-6, same prompt. Claude-Muse kappa_major 0.74-0.85 (b2-b4) and 0.658 (b6). Free; our call budget 200 calls an hour, 1,500 a day soft, shared with other lanes. |
| Fallback for Claude stops | Gemini 3.8 Flash, one configuration (below) | Calibration, 22 Oct: on 100 batch 2-4 gold items (seed 66), exact 0.89, kappa_major 0.887. This rests on about 10 majors (10 called, 9 right), so it is weak evidence, not strong. Second fallback: Grok 4.7 (kappa_major 0.50 on the same items, via OpenRouter), used only if Gemini cannot run for 48 hours. |
| Third blind read (disagreements only) | Gemini 3.8 Flash, same configuration | Gives a 2-of-3 blind majority as a check on the Claude-led adjudication |

**Gemini configuration, fixed now.** Model `gemini-3.8-flash`, default thinking (no thinking setting), the v2 rules
and user message of `judge_v2.py`. This is the calibration configuration: the calibration ran 7 reads on the free key
through `gemini_read.py` and 93 on OpenRouter `google/gemini-3.8-flash`, both with default thinking (PREREG_SYSTEM
22 Oct, 5:22 PM note). Host order: (1) the owner's free Gemini key through `scripts/gemini_read.py`, unchanged;
(2) OpenRouter through `scripts/openrouter_read.py --model google/gemini-3.8-flash`, paid, only with the owner's yes
for that run. Not used: a second Gemini route (its ids are `gemini-3.8-flash-high/-medium/-low`, a thinking level never calibrated) and
`alt_calls.gemini_key` (sets thinking high). Each host writes its own file (`ref-fb-gemini-key.jsonl`,
`ref-fb-gemini-or.jsonl`; third reads `third-gemini-key.jsonl`, `third-gemini-or.jsonl`), and gemini_read.py records
`modelVersion` per row. Fallback and third reads are reported by host.

How fallback reads join the key: the fallback files sit in `b7/ref_claude/` with the same JSONL fields as the Claude
rows (draw, citation_type, verdict, reason, plus model), so gold.py's Claude glob `b7/ref_claude/ref-*.jsonl` reads
them as reader A. The `model` field shows which reader each row came from.

Batch 6 difference to note: batch 6 used Grok 4.7 as the primary reader for its 66 Claude-stop items, with Gemini as
a second check (PREREG_SYSTEM amendment 4). Batch 7 uses Gemini first. Both batches are also reported without
fallback-read items, which makes the batch 6 to batch 7 comparison free of this difference.

Rejected for reader 2: Gemini (best single reader, but the free key 429s after about 125 calls a day and the second route's
weekly quota ran out after about 300-450 calls across all models on 29 Oct, so 1,320 reads would not finish on free
capacity); GPT-OSS 120B (it was a screen arm in the batch 6 system choice, and has no accuracy-task reader
calibration); Grok 4.7 (kappa_major 0.50).

Conflict settled by this draft (owner decision 1): NEXT_ROUND_CANDIDATES lists Gemini 3.8 Flash as a candidate
system. A reference reader must not be a candidate scored on its own reads (the fallback is not a candidate
system). This draft moves Gemini 3.8 Flash from candidate to reference reader for every test scored on batch 7. If
the owner keeps it as a candidate, the fallback and third read become Grok 4.7 and the 2-of-3 check is dropped.

### Part B
| Role | Reader | Evidence |
|---|---|---|
| Reader 1 | Claude Opus 5.5 on the API, effort medium, the census codebook v3.3 prompt and parse (`classify.SYSTEM`, `classify.user_msg`, `classify.parse`), one request per passage (`econ-pilot anthropic_calib.py` arm "opus", reading `partb_records.jsonl`) | Claude Opus 5.5 wrote the confirm_v33 key; check 31 Oct: 140/147 = 95.2% on confirm_v33 (bar 95%; Haiku 5.5 got 98.0% on 30 Oct) |
| Reader 2 | Muse via `fill_alt.py` route plan (the 29 Oct backup-reader set-up) | Muse calibration 30 Oct: 144/150 = 96.0% on confirm_v33, 194/194 contexts, 0 errors |
| Fallback for Claude stops | GPT-OSS 120B (`gpt-oss-120b-medium`) | 137/150 = 91.3% on confirm_v33. Not a census panel member. Gemini is not used in Part B: it shares a maker with Gemma, a census panel member. |

Answers become labels through `classify.label()`, the same rule the panel and the human sheets use. A pair takes its
strongest passage label. B2 readers use the census codebook, not the Lists full-read rule, and see the citing passage
only, not the full text (section 7 says what that means for the result).

## 5. Adjudication

- `scripts/gold.py` (Part A) and the same rule for Part B: readers agree on the verdict (Part A) or pair label
  (Part B), that is the key. They disagree: a third careful read decides.
- gold.py writes all disagreements into one `adjudicate.md` and prints the reader agreement rate. It is run through
  a wrapper (`b7/run_gold.sh`, new) that seals gold.py's printed summary (`b7/gold/.sealed_summary.json`, read-only,
  not opened before scoring) and shows only the number of items to adjudicate. `b7/adj_items.py` (new) cuts
  adjudicate.md into one request per item in draw order and sets aside every draw Claude refused as reader 1 (those
  disagreements go to Grok, below), so no Claude request carries an item Claude stopped on.
- Adjudicator: Claude Opus 5.5 on the API, effort high, one request per item, a fresh context each time. It sees the
  item, both verdicts and both reasons, never any system or panel output. System prompt `b7/adj/ADJ_SYSTEM.md`: the
  v2 rules plus the batch 6 `ADJ_RULES.md` adjudicator instructions, without the file-handling lines.
- Part A sensitivity: on the same disagreement items, Gemini's blind third read gives a 2-of-3 majority (Claude,
  Muse, Gemini). Report how often it differs from the adjudicated key. If it differs on more than 15% of disagreement
  items, report every rate both ways.
- Adjudication stops (a Claude refusal on an adjudication request): Part A, the 2-of-3 blind majority decides; a
  three-way split stays "cannot_tell" and leaves the judged base. Part B, GPT-OSS 120B adjudicates with the same text.
  Part B items Claude stopped on as reader 1 are never sent to Claude again; where GPT-OSS (their reader 1) and Muse
  disagree, the item is "no key" and counted in coverage (expected 2-4 items).
- An item Claude stopped on is never sent to Claude again, in any request (C8.3: no retry of the same content).
  Where the fallback reader (Gemini) and Muse disagree on such an item, Grok 4.7 adjudicates with the
  same text (C8.4 names it; not a candidate system). Its reader kappa_major was 0.50, so every Part A rate is
  also reported without these items. Expected: about 15 items.
- "cannot_tell" key items are left out of every rate (as batch 6). Every rate names its base.

## 6. Safety stops

One request per item, so a stop costs one item, not a packet. A refusal (stop_reason "refusal") is final for that
item and that reader: no retry, rewording or re-splitting. `scripts/anthropic_read.py` records every refusal in
`logs/claude_stops.json` and skips any listed item in every later submit; `b7/api_to_ref.py` lists them in
`b7/ref_claude/stops.json`, and they go to the fallback reader above. A technical failure (errored, expired,
max_tokens, invalid JSON) is not a stop: it is re-sent once with the same content, and a second failure goes to the
fallback reader too. The run works by draw number and never prints article text (C8.2). Expected from the
calibration: about 1.8% of Part A items (3 of 164) and about 2% of Part B passages (4 of 194); batch 6's Claude
packets lost 6.6%. Methods report coverage per reader ("N Claude, N Gemini after stops", Gemini by host) and every
primary rate also without fallback-read items.

## 7. Success measures (scored once, after all reads are in; no interim looks)

Part A, primary:
1. Coverage: at least 95% of the reading set gets two blind reads and a key (fallback reads count).
2. Size: at least 1,000 judged and at least 60 key majors. Expected: about 1,213 judged, about 87 majors.
3. Reader agreement (the ceiling): Claude-Muse kappa_major at least 0.60. Below 0.60 the key is reported as weak and
   is not used to score any system or to move a site figure.
4. Major rate and any-error rate with Wilson 95% intervals. Expected major CI on batch 7 alone about 5.9-8.8%.
5. Pooling, fixed now (not after the result). The pooled batch 6+7 estimate, with batch as a stratum, is always
   reported beside both batch figures (expected about 153 of 2,128, CI about 6.2-8.4%). The headline moves to the
   pooled figure only if all of these hold: (a) the 90% Newcombe interval for the batch 7 minus batch 6 major rate
   lies inside plus or minus 3.0 points (an equivalence test, not "no significant difference"); (b) the canary passes
   its tolerance (at least 28 of 33); (c) the ceiling holds (item 3). Otherwise batch 6 stays the headline and batch 7
   is shown beside it. Power: the standard error of the difference is about 1.13 points, so a 95% test has 80% power
   only for a gap of about 3.2 points. Under the equivalence rule, if the batches truly match the headline pools about
   69% of the time; with a true 1-point gap about 52%; with a true 2-point gap about 22%.
6. Citation-type comparison, pre-registered here: major rate for specific_claim against background, Newcombe 95%
   interval on batch 7 alone. Batch 6 showed 9.7% vs 5.6%; batch 7 has about 70% power to see a gap that size.

Part A, secondary: adjudication stability (section 5); canary results; rates without fallback items (both batches);
rates without the Grok-adjudicated items; reader 2 and fallback readers' agreement with the key, by host.

Part A, system confirmation (scored once, with the rest). The frozen setup (`FROZEN_SETUP_2026-10-30.md`: Composer
2.5 screen at 10 per call, then three Claude Haiku 5.5 xhigh reads, major if any says major; Claude refusals to Grok
4.7) is run on the batch 7 reading set after registration, blind to every reference read, with the hashed scripts
and settings named there. Its output is sealed until scoring. Bars as before: kappa_major at least 0.60, recall at
least 0.70, precision at least 0.65, against the adjudicated key. Because the deciders are Claude models and Claude is
reader 1 and adjudicator, it is also scored (a) on items where the two readers agreed (no adjudicator) and (b)
against Muse's reads alone (a non-Claude reader). On batch 6 the setup scored 0.795 primary, 0.915 on agreed items
and 0.707 against Muse alone. If (b) falls below 0.60 while the primary passes, the result is reported as "passes
against a Claude-led key only". The backup screen (Grok 4.6 medium, 10 per call) is scored the same way as a
secondary arm. In this run an item already in the Claude stop registry (`logs/claude_stops.json`: refused by any
Claude model, reader 1 included) is not sent to Haiku (C8.3); it goes straight to Grok 4.7, the setup's refusal route,
and is counted as such. `b7/score_b7.py --system` computes all of these.

Part B (internal and exploratory; each stratum alone, never pooled with Part A):
1. B3 unanimous: key agreement with the panel label, and on the headline question (cited as support or not). Bar:
   at least 95% agreement on the headline question.
2. B2: **census-codebook agreement on Lists citations**, the share of counted Lists citations the codebook key also
   calls "cited as support". Reported in two parts: citations whose List label is a census label, and citations whose
   List label came from the full read. Bar: at least 90%. This is not a check of the List counts: the List counts use
   the full-read rule (METHOD.md sections 5 and 8: methods citations and citations in a group are treated
   differently, and full-read readers see the citing paper's full text, the abstract and the notice). A codebook key
   below 90% cannot by itself show that a List count is wrong.
3. B1 disagreements: which way the key falls (panel majority, strict or lenient reading), with Wilson intervals.
4. Claude-Muse agreement (kappa) per stratum. Below 0.60 in a stratum, that stratum's result is reported as weak.
5. Exploratory, labelled as such: a design-weighted panel sensitivity and false-positive rate from B1 and B3 (weights
   8,063 and 43,551, the judged pools), beside the confirm_v33 figures (96.5% and 6.5%).
6. `human_score.py` is used only for its Claude-Muse agreement and per-stratum counts. Its `rule_85` field and its
   "headline must be reported with this agreement..." message are built for the random human 200; on these targeted
   strata they are ignored and never quoted.

## 8. What each result would change on the site

Rules that hold whatever the result: every figure says it is measured against AI reads and carries "pending human
review". Nothing is called "validated" alone or human-checked. Figures reach any page only through `facts.py`, in
new blocks (`stage3b`; Part B, if anything is ever shown, `census_check`). `census_p2` is frozen (SOP line 452: a
rerun gets a new block, never a re-ingest). `stage3` has no freeze note, but batch 7 still goes in its own block so
the published batch 6 figures stay quotable. Anything that would change a published figure goes to the owner the same
day before it moves (SOP start-here item 4).

| Result | Site change |
|---|---|
| Part A pools (section 7, item 5: equivalence, canary and ceiling all pass) | Checker page and home #accuracy: the headline major and any-error rates move to the pooled batch 6+7 figures with the narrower interval and the base "two random sets, about 2,100 judged". |
| Frozen setup passes on batch 7 | Owner decides whether the checker page describes the new setup. If yes, its batch 7 scores go in a new facts block with "measured against AI reads, pending human review"; the locked Cloudflare system's batch 6 scores stay quotable as history. |
| Frozen setup fails on batch 7 | No site change; the setup is not used for published figures. Logged, and the owner told the same day. |
| Part A does not pool | Batch 6 stays the headline; batch 7 is shown beside it with its own base. If the two differ significantly, the gap is logged and looked into (sampler, reader model, chance) before any further use. |
| Ceiling below 0.60 | No site change. The key is logged as weak; the human check moves up. |
| Fewer than 60 key majors, or fewer than 1,000 judged | No site change. The key is logged as short and kept as a scoring set for later candidates only, with its size stated. |
| Coverage below 95% | No site change. The key is logged as incomplete, with coverage per reader; it can be used later only beside a statement of what it misses. |
| Citation-type gap confirmed | The "specific findings are riskiest" line drops "This comparison was not in the test's plan" and cites the pre-registered batch 7 test. |
| Citation-type gap not confirmed | That line is cut from the site and llms.txt. |
| Part B, any result | No change to any census figure, error note or correction (Part B is internal). Owner told the same day of each stratum's result. B3 below 95% or B1 results are inputs to a registered census amendment with a human check, if the owner wants one. |
| B2 below 90% | No List count moves on this result. Owner the same day. The owner may order a re-read of the affected entries under the Lists full-read rule; only that re-read can move a count, by a dated correction (A4). No letters from this run. |

## 9. What this sets up (not part of this run)

- Human check of accuracy: draw from batch 6+7 (about 2,100 judged): every key "major" plus an equal random draw of
  the rest, double-coded by two people, scored like `human_score.py`. With about 150 key majors that gives a usable
  estimate of how often an AI "major" is right. Needs paid labellers (a grant).
- Human check of the census targeted strata (IMPROVEMENT_PLAN item 5 as planned): the Part B sheets are already in
  the human packet format. That check, and any census use of the canary, need the registered census amendment.
- Cascade bake-off (IMPROVEMENT_PLAN item 8) and next-round candidates: batch 6+7 is their scoring set, under their
  own pre-registrations.

## 10. Registration and changes after registration

- Public timestamp (owner decision 2, approved 30 Oct): `PREREG_HASHES.txt` with the sha256 of this document and
  of every new or changed script is committed to the public census repo (GitHub MrSaneApps/sanecite-retraction-
  census) before sampling. The document itself stays private until the result is published.
- Changes after registration are logged in `DEVIATIONS.md` with date and time, and whether any result had been seen.
  No rule in sections 3-7 changes after the first reader output exists, except to keep coverage (a reader host that
  dies), and then only by a dated amendment written before that reader's output is looked at.
