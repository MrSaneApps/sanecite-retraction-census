# Lists downloads: what the columns mean

Written by tools/lists.py. Corrections applied on top of the generated data are in
/data/phase2/list_corrections.json, each with its source.

## Where dates and reasons come from

- `retraction_year_notice`, `reason_notice` (papers.csv, all-papers.csv): from the journal's retraction notice.
  `reason_source` names the notice. "not yet read" means we have not read that notice first-hand.
- `retraction_year_retraction_watch` (papers.csv, all-papers.csv): the year in the Retraction Watch database.
  It can differ from the notice; the census uses it except where list_corrections.json gives the notice date.
- `reason_group_retraction_watch` (papers.csv, all-papers.csv): grouped from Retraction Watch codes, not the notice's wording.
  A group such as "misconduct, fabrication or duplication" bundles reasons a given notice may never state.
- `retraction_reason` in /data/phase2/citations.csv: the same grouping, from Retraction Watch codes, not the notice's wording.
- `retraction_year` in /data/phase2/citations.csv: the Retraction Watch year.

## author-items.csv

One row per citation on the author list.
- `notice_reason_class`: results (the notice names a problem with the data, images or results, or says they cannot be
  relied on) or unclear (no reason, a vague one, or not yet read; still counted). Citations of work retracted only for
  reasons that do not touch the results (reused text, a duplicate of a result that stays published, authorship, ethics
  paperwork, copyright or a software licence, a wrong journal) are left out of every list and count here; they are
  published in excluded-works.csv and excluded-citations.csv.
- `reference_list_shows_retraction`: 1 if the citing paper's published reference list links the retraction notice or
  labels the work retracted. Such links are often added automatically during publication, from the cited record, so
  they do not show the authors knew.
- `timeline`: printed where the citing paper was submitted or accepted before the retraction.
- `citing_paper_retracted`: the citing paper has itself been retracted since.
- `retraction_year`: as printed in our letters, with later corrections.

## replies.csv

Everyone named was written to before publication, and told that replies received by 28 October would be
summarised fairly on the page. Every reply gets the same treatment (one rule for everyone): a summary in our words, one short
verbatim quote, and any statement the writer supplied for publication, printed as written. One row per reply. The same fields are in /data/phase2/list_corrections.json under `replies`.
- `list`, `entry_id`: the entry the reply belongs to: an author's ORCID iD, a retracted paper's PMID or a citing
  journal's name. The build stops if the entry does not exist.
- `shown`: "on the page", printed under the entry; or "downloadable data only" for a paper retracted for reasons that do
  not touch its results, which is not named on the page.
- `received`: the date the reply reached us. `from_role`: who wrote, by role (the author, the editor).
- `reply_by`: the reply date stated in our letter to that entry. `late`: "received after the reply date" when the
  reply came later; a late reply is still printed, with its date.
- `summary`: two to four sentences in our words, giving the writer's main points, including those against us.
- `quote`: one short passage in the writer's own words (under 40 words), chosen by a fixed rule: the sentence that states
  their main point. Spelling and grammar are left as written.
- `statement`: a statement the writer supplied for publication (for example a note for later authors), printed as
  written, paragraphs separated by a blank line; empty if none was supplied. Greetings, sign-offs and contact details are
  left off.
- `our_response`: what changed because of the reply, or why the entry stands, with the facts.
- `changes_since_letter`: every change to the entry since our letter, separated by " | ", whether the reply prompted it
  or a rule applied to every entry did.
- Not published: where each reply came from (kept privately, so the build can check every reply has a source).
  No reply is left out, and no one is asked for permission to be quoted; replies are never trimmed to win a point.
  Contact details and third-party personal data are removed from everything printed. An automatic reply or a bare
  acknowledgement is not a reply and is not summarised.

## second-reading.csv

Every citation read a second time, limited to citations still in scope after the corrections. Readings of citations to
work retracted for reasons that do not touch the results are not included.
- `second_reading`: the verdict of the second reading. `note`: the reader's one-line reason.
- `final_verdict`: the verdict the lists count. It is the second reading, unless a later full-text check of the same
  citation (list_corrections.json `relabel`) gave another label; then it is that label.
- `reading_round`: which reading gave the final verdict: "second reading", or "full read" with its date (for a few
  papers near the last place, "full read, two blind readings and a third reader").
- All of these are AI readings. Everyone named was sent the evidence and asked to tell us if a reading is
  wrong.

## all-papers.csv and all-journals.csv

Every retracted paper and citing journal in the lists' scope, ranked by the count of citations cited as support. The
counts carry the corrections in list_corrections.json (label corrections from the full-text checks, dates from the
notices, citations made before a retraction left out); only the listed entries and the papers near the last place were
read again. `census_cited_as_support` and `census_judged` (all-papers.csv) give the census labels alone, so every
difference can be traced. 1 paper is held out of all-papers.csv until it is named; its corrections still count in the journal tables.

## excluded-works.csv and excluded-citations.csv

The papers retracted only for reasons that do not touch the results, and every judged citation of them made after the
retraction, with the census label. They are left out of every count and list, not hidden.
- `notice_says` (excluded-works.csv): the notice's reason, in its own words where quoted.
- `census_label`: substantive (cited as support), perfunctory (mentioned in passing) or aware (flagged as retracted
  or unreliable). Not read a second time.
