# How the SaneCite Lists count "cited as support"

Written 23 October 2026. It describes the Lists as built from the branch audit-20261022-lists (tools/lists.py with
data/phase2/list_corrections.json and the private tools/held.json, which lists.py merges in at build time). Where this
file and the code disagree, the code decides; fix this file the same day and say which commit it was checked against
(last check: 677acf8, 23 Oct 2026). Plain-English summary first, then each rule with the code that applies it.

## In short
The Lists start from the census labels and then apply corrections, each with its source, at build time. Six
things make a List count differ from a census count:
1. Works retracted only for reasons that do not touch their results are left out.
2. Retraction dates come from the notice, and a citation counts only if the citing paper went online after it.
3. Only retractions PubMed links to a notice are in scope.
4. Every paper that could reach the last place was read in full, and a different rule for close calls decides each
   citation (the "full-read rule" below), which differs from the census codebook in two ways.
5. A reference printed with the notice's own title is a citation of the notice, not of the paper.
6. The full read only re-reads citations the census called "cited as support". It can lower a count; it never
   raises one.

The labels keep their census names: "cited as support", "mentioned in passing", "flagged as retracted or
unreliable". All readings are AI readings. Everyone named was written to and can reply; replies are printed beside
their entries.

## 1. The starting point: census labels
The census panel (three models) labels each citing passage. Its fixed rule, applied by code (protocol/codebook.md,
"From answers to a label"):

    2. stance = disputed: aware.
    3. use = counted, and the passage has a counting word ...: substantive.
    4. n >= 2 (cited together with other references): perfunctory.
    5. use = specific: substantive. use = unclear: unclear. Otherwise: perfunctory.

"substantive" is printed as "cited as support", "perfunctory" as "mentioned in passing", "aware" as "flagged as
retracted or unreliable". A citing paper takes its strongest passage label.

## 2. Scope of the Lists
tools/lists.py, in_scope():

    judged citations (paperwork retractions and unclear labels left out) to papers PubMed links to a retraction
    notice. Replaced originals, records that are the replacement, and unconfirmed ones are left out.

So a citation labelled "unclear" (including one the full read moved there, section 4) leaves the judged base.

## 3. Reason-class exclusion
list_corrections.json, excluded_works_rule:

    Citations of a work are left out when its retraction notice gives only reasons that do not touch the results:
    author withdrawal with a stated non-results reason, ethics paperwork, redundant or duplicate publication of a
    result that stays published, plagiarism or reuse of text only, copyright or software-licence changes, a wrong
    journal, or forged or disputed authorship. Figure or image duplication or reuse, data problems, errors,
    fabrication, paper mills and compromised peer review still count. A notice with no stated reason, or an unclear
    one, still counts and is marked reason unclear. Applied where we have read the notice.

The excluded works and their citations are not hidden: they are published in excluded-works.csv and
excluded-citations.csv. The census has no such exclusion (it leaves out only administrative retractions).

## 4. Dates and the first-online window
The census uses the Retraction Watch year. The Lists use the notice's date where list_corrections.json gives it
("retraction_dates", each with its notice PMID), and lists.py drops citations made before it (corrected_rows()).
A citation found in the full read to be published online before the notice is excluded with the reason
"Published online before the retraction notice." First-online dates are Europe PMC firstPublicationDate or the
publisher's online date, never a Crossref registration date (SOP B11).

## 5. The full read
Which papers: SOP B5. Before a paper is named at or near the last place, every paper whose current count could reach
that place (listed, removed or unread) is read in full, the full-read labels are applied to all of them, and the
recount is repeated after each batch until no paper can enter or leave. On 23 Oct 2026 that was 21 papers: 20 in
list_corrections.json "full_read" plus 1 held entry in tools/held.json (held until its authors have had the same time
to reply; lists.py adds it to the full-read set at build time). Why: reading only some papers near the cut swaps who is named (a full read kept
22 of 31, 22 of 30 and 26 of 30 citations).

What is read: every citation the census counted as "cited as support" for those papers, checked against the citing
paper's full text (Europe PMC or PMC) and the retracted paper's abstract and notice. For the papers at and just below
the last places, each citation was read twice, blind, and a third reader settled the disagreements; the majority
decides (outreach/drafts/round2-fullread/apply_round2.py).

Verdicts (outreach/drafts/round2-fullread/BRIEF.md):

    HOLDS: presents as established something the retracted paper reported, and uses it as support.
    NOT_IN_PAPER: credits the retracted paper with something it does not report.
    PASSING: background mention where no result of the retracted paper is carried forward.
    FLAGGED: warns readers the work was retracted, disputed or unreliable (in the text near the citation, by the
      authors).
    WRONG_REFERENCE: the marker does not point to the retracted paper, or the printed reference is the notice.
    CANNOT_CHECK: no full text reachable.

How each verdict changes the List (outreach/drafts/place10-fullread/apply_fullread.py):

    PASSING -> perfunctory, NOT_IN_PAPER -> unclear, FLAGGED -> aware (relabel); WRONG_REFERENCE or online before
    the notice -> exclude_citing; HOLDS and CANNOT_CHECK -> no change.

Each change is written to list_corrections.json ("relabel" or "exclude_citing") with its source and date, and
lists.py applies it at build time. The build stops if a relabel names a citation that is not in the data or holds an
unexpected label, so a regenerated data file cannot undo a correction silently.

## 6. The rule for close calls (fixed 23 Oct 2026)
From BRIEF.md, applied exactly:

    The test is whether the citing sentence carries a RESULT of the retracted paper forward, not how many references
    sit nearby or whether it is a list.
    - HOLDS when the sentence (or the table row) states a result the paper reported: a direction, an effect, a
      mechanism, a target, a number. This applies even inside a list, even when hedged ("may", "suggested"), and
      even when other references are cited for other parts of the sentence.
    - PASSING when the paper is cited only for a topic, a disease, a context or a field, with no result carried
      forward. Also PASSING: a citation only for a general fact the paper itself took from others, or one reference
      among several for a generic claim that no single one of them established.
    - Methods use: citing the paper only for a technique or protocol is PASSING. Using the paper's own instrument,
      scale, cut-off or validity values is HOLDS, because the retraction concerns that measure's validity.
    - If the sentence carries a result forward but distorts it, it is HOLDS when the core result is the paper's own,
      NOT_IN_PAPER when the core claim is not in the paper.

## 7. The printed-title rule
From apply_round2.py: "Printed-title rule for references: the article's own title = the paper (counts); the
notice's 'Retraction: ...' title = the notice (wrong reference)." A reference entry printed with the notice's title
is a citation of the notice, so it is excluded as WRONG_REFERENCE. Labels that PMC, Europe PMC or a publisher add
automatically (a "retraction-forward" link, a "Retracted:" prefix) are not the authors' own and do not by themselves
make an entry a citation of the notice.

## 8. How List counts differ from the census codebook
1. Methods citations. The codebook counts "Cells were treated as described previously [->6]" as specific, so
   substantive ("cited as support"). The full-read rule calls a citation only for a technique or protocol PASSING.
   Using the paper's own instrument, scale or cut-offs stays HOLDS.
2. Citations in a list. The codebook makes any citation with n >= 2 "mentioned in passing" (rule 4, before rule 5).
   The full-read rule keeps a citation as support even inside a list when the sentence states a result of the paper.
3. One direction only. The full read re-reads only citations the census labelled "cited as support" (each relabel
   has old = "substantive"). A citation the census called "mentioned in passing" under rule 4 stays so, even where
   the full-read rule would say HOLDS. So for a fully read paper the List count is the citations that pass both
   rules, never more than the census count.
4. Papers not in the full-read set keep their census labels, checked by a sampled second reading
   (second-reading.csv). The read set (section 5) makes sure no unread paper could reach a listed place.
5. Scope and dates: sections 2 to 4 apply to every List count and to no census count.

## Where the pieces are
- Corrections and their sources: data/phase2/list_corrections.json (published with the Lists).
- The code that applies them: tools/lists.py (site repo, Lists branch).
- Full-read briefs, results and the scripts that turned results into corrections: outreach/drafts/round2-fullread/
  and outreach/drafts/place10-fullread/ in the ops folder (private: they sit beside letter drafts). The scripts and
  BRIEF.md files are in the ops git repo since 23 Oct 2026; letter text and data are not.
- The rules that govern reading and naming: SANECITE_SOP.md, B1-B13.

## Not yet done (owner decisions, 23 Oct 2026)
- The census protocol (protocol/PROTOCOL.md) has no amendment for these rules; its amendments stop at 11, and its
  heading says none was made after seeing final results. An amendment 12 written now would come after the Lists were
  built and must say so. Owner to choose: a dated amendment 12 that says so, or this file published with the Lists
  CSVs as the method of record (audit finding 16).
- A public copy of this file for the Lists folder: drop the ops paths (outreach/drafts/..., SANECITE_SOP.md) and the
  private tools/held.json detail, keep the rules. It goes on the Lists branch, not here.
- The Lists page should say in one line that List counts use the full-read rule, which differs from the census label
  in the two ways in section 8 (Lists branch, not this file).
