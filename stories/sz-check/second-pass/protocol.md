<!-- Public copy, published 9 Nov 2026. The protocol was written and its SHA-256 hash recorded on 9 Nov 2026 before any flag was read (hash of the original: db6646c14d826b792302ae4db0bed944c2224facf0bb85f95514b8d87e2e6802). This copy removes internal notes and file names; the questions, grades and rules are worded as in the original. -->

# Pre-registration: second pass on the 99 "disputed choice of method" flags (9 Nov 2026, written before any reading)

Question (9 Nov 2026): of the 99 flags we called "depends on a disputed choice of method", are the
choices really standard and justified, or questionable?

Population: the 99 flags whose published verdict (https://sanecite.com/data/sz-check/verdicts.json, 9 Nov 2026) is "depends on a disputed
choice of method". List: the 99 ranks in adjudication.json.

Question Q3 (one per flag): how contested is the method choice the flag turns on?
- STANDARD: the paper states the choice (text, appendix, or code comments), and the choice is used in comparable
  published work that the paper or the flag itself cites. A reader of the paper could see it and find it common.
- DEFENSIBLE, NOT DISCLOSED: a reasonable choice, but the paper does not state it, or does not show how the result
  changes under the main alternative the flag raises.
- QUESTIONABLE: the choice departs from the paper's own stated method, from the documentation of the data it uses, or
  from the practice of the sources the paper itself cites, and the paper gives no reason for the departure.
- CANNOT TELL: the material needed is not public or not reachable.
Plus RECLASSIFY (yes/no): yes only if the evidence meets rule R2 of our written adjudication rules of 29 Oct 2026 (a recomputation
or the paper's own numbers show a headline NUMBER changes) AND the issue is a departure from the paper's own stated
rule or data rather than a choice reasonable researchers dispute. A yes is a candidate for "changes a headline number"
and is reported separately; it never changes the published verdict without a new right-of-reply letter (our right-of-reply rule; replaced by amendment 1).

Evidence rules (as R6): open only the paper (the version the flag cites), its appendix, code and data, the pages the
flag cites, works the paper or the flag cites, and the authors' own related papers. No new literature search. Every
grade other than CANNOT TELL names a page, table, file or quote a person can redo. The first pass's evidence
(our first-pass evidence for each flag) may be reused and must be cited when it is.

Readers: reader A = Claude (Anthropic), in batches of about 20 flags, writing a grade and an evidence note for each flag. Reader B = a model from another family, given the flag and the text of the pages reader A cites, blind to
A's grades. Disagreements: settled from the evidence under these rules,
with a written note; unresolvable ones reported as CONTESTED.

Reported: counts of each grade with Wilson 95% intervals; RECLASSIFY candidates listed one by one with evidence;
agreement A vs B. Private until red-teamed and final.
Not claimed: nothing about intent; "standard" means used in the cited literature, not "correct".
Known bias: the audit used Claude; reader A is Claude, which is why reader B is another family.
