# SaneCite Phase 2 codebook, v2 (2026-10-13)

v2 adds three rules after the first bakeoff showed the boundary cases: lists with one
reference per item, studies counted in a review, and pure descriptions. The live prompt
is `scripts/classify.py` (CRITERIA, RULE, EXAMPLES); this file explains it.

Unit: one post-retraction citation, i.e. one citing paper citing one retracted paper,
judged from the sentence that carries the in-text citation, plus one sentence either side.

| Label | Rule |
|---|---|
| aware | The citing text says the cited work was retracted, withdrawn, discredited, fraudulent, wrong, or disputes it. |
| substantive | The citing authors use this paper's specific result, method, data or numbers as support, and it is the sole or main reference for that specific claim. Includes papers counted as included studies in a review or meta-analysis, "consistent with [x]", "as described by [x]". |
| perfunctory | The paper is one of a bundle of references behind a claim, or backs a broad or general statement (definitions, field-level facts, lists of applications), or is only described ("X et al. used ML to ..."), not used. |
| unclear | The context is garbled or too short to judge. Excluded from rates and reported. |

Test for substantive vs perfunctory: remove this one reference. If the specific point still stands on the others or on common knowledge, it is perfunctory.

- Lists: when each item has its own reference, judge only the item this reference backs.
- Reviews: studies counted or pooled as data are substantive even when cited together.
- Descriptions: "X et al. used Y to study Z" with no result used as support is perfunctory.

Separate flag, not a label: `ref_label_retracted`: the citing paper's own reference entry for the work carries a "Retracted" / "Retraction in" marker.
