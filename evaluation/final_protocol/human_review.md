# Held-out ground-truth review

AI-assisted review status: **COMPLETE**
Review date: 2026-09-07
Human reviewer count: 0
`SINGLE_ANNOTATOR_GROUND_TRUTH = YES`

`HUMAN_GROUND_TRUTH_REVIEW = NO`
`AI_ASSISTED_GROUND_TRUTH_AUTHORING = YES`
`AI_ASSISTED_GROUND_TRUTH_REVIEW = YES`

An AI agent authored and inspected every narrative for event count and type, trigger substring and offsets, subject role and exact third-party text, date substring and offsets, normalized interval, ambiguity, safety annotations, sampling categories, and shared proper-name/date NER spans. Schema validation was run after the review. There is no evidence that a human user reviewed all 100 records.

| Narrative IDs | AI-assisted review | Result |
|---|---:|---|
| heldout_001–heldout_010 | 10/10 | PASS |
| heldout_011–heldout_020 | 10/10 | PASS |
| heldout_021–heldout_030 | 10/10 | PASS |
| heldout_031–heldout_040 | 10/10 | PASS |
| heldout_041–heldout_050 | 10/10 | PASS |
| heldout_051–heldout_060 | 10/10 | PASS |
| heldout_061–heldout_070 | 10/10 | PASS |
| heldout_071–heldout_080 | 10/10 | PASS |
| heldout_081–heldout_090 | 10/10 | PASS |
| heldout_091–heldout_100 | 10/10 | PASS |

## Corrections made before freezing

- `heldout_008`: removed an explicit `eu` so the predeclared pro-drop category is truthful.
- `heldout_041`: replaced an unnatural event wording with two explicit kinship subjects.
- `heldout_046`: corrected the authored occurrence index for the second case-sensitive trigger.
- `heldout_092`: replaced a negative sentence that could imply a specific marriage.
- `heldout_021`: added a positive `natimorto` case to cover the complete approved event scope.
- `heldout_037`: added one explicit marriage participant for exploratory participant scoring.
- `heldout_043` and `heldout_048`: made coordinated-human-subject abstention directly evaluable.
- Reported-speech and incidental-person cases received explicit excluded-subject annotations for leakage metrics.
- The B1 shared-task layer was completed before freeze with 88 proper-name PERSON spans and 120 DATE spans, including distractor years.

No model output was viewed or produced during authoring or review. After this file and the manifest were finalized, the dataset hash was frozen and no further dataset edits are permitted.

## Limitation

`SINGLE_ANNOTATOR_GROUND_TRUTH` means one AI-assisted authoring/review provenance stream; it does not mean one human annotator. No human review and no inter-annotator agreement are claimed. A future explicit human review may update review metadata without silently changing the frozen test content; discrepancies requiring content changes would require a versioned replacement dataset.
