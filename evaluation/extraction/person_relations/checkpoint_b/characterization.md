# Person-Relation V1 Checkpoint B Characterization

## Boundary and data

This is a development/adversarial comparison, not a final evaluation. It uses the approved 124-case corpus plus 56 new risk-motivated cases (180 narratives and 165 expected candidates). The original corpus contains replacement characters (`�`) in accented Portuguese text; it was preserved rather than reconstructed. New cases use valid UTF-8. This limitation can depress model-based detector performance and prevents treating these results as population estimates.

All strategies feed the same deterministic normalizer, endpoint associator, compositional guards, candidate constructor, oracle, and metrics. No strategy is connected to an API, review flow, graph, UI, or REF.

## Configurations

- **A0:** inspectable lexical detection of the nine approved surface families in copular or explicitly coordinated claim structures.
- **B:** `fastino/gliner2.5-multi-v1` at revision `aaecfe45db1d828c963717054ccb868e8ad1f1d5`, using six natural-language class labels recorded in `experiment_config.json`.
- **C:** the same model and revision with the generic label `person relationship expression`.
- **B/C threshold grid:** 0.20, 0.30, 0.40, 0.50, 0.60, 0.70. One 0.20 inference was filtered for higher thresholds. Safety-first selection chose B=0.50 and C=0.20.

## Detector-only results

| Strategy | Precision | Recall | F1 | Exact span | Overlap | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| A0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 |
| B (0.50) | 0.0899 | 0.2012 | 0.1243 | 0.0000 | 0.2012 | 334 | 131 |
| C (0.20) | 0.0672 | 0.1585 | 0.0944 | 0.0000 | 0.1585 | 361 | 138 |

GLiNER usually returned broader or unrelated spans, explaining zero exact-span rate and many detector false positives. The strict shared lexical normalizer/context filter rejected those unsupported spans, so they did not become false `RelationCandidate` objects. B recovered more relation evidence than C, but both missed most spouse, coordination, reported, and compositional examples at their selected thresholds.

## End-to-end results

| Strategy | Precision | Recall | F1 | Type | Endpoint A | Endpoint B | Both | Polarity | Epistemic | Reporting | Temporal | False candidates | Wrong resolved endpoint | Unsafe persistible FP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9576 | 0.9576 | 0.9152 | 1.0000 | 1.0000 | 1.0000 | 0.9939 | 0 | 0 | 0 |
| B | 1.0000 | 0.2000 | 0.3333 | 1.0000 | 0.9697 | 1.0000 | 0.9697 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 0 |
| C | 1.0000 | 0.1576 | 0.2723 | 1.0000 | 1.0000 | 0.9615 | 0.9615 | 1.0000 | 1.0000 | 1.0000 | 0.9615 | 0 | 0 | 0 |

Endpoint accuracy counts preserved generic/pronominal text against the oracle, so conservative unresolved text may reduce accuracy without being a wrong resolution. The four initial wrong endpoint resolutions on `filho/filha/irmão/irmã de criação` were removed by a narrow shared regression rule. The only remaining A0 temporal mismatch is PR-018: its oracle marks `nunca foi mãe de` as current/unspecified, whereas another minimal pair (PR-133) marks the same past verb pattern as past. The implementation retains the verb-based `PAST` interpretation; this mismatch is non-persistible through negation and is not a safety-gate failure.

## Safety and abstention

Every selected configuration passed both hard development gates:

| Strategy | Wrong endpoint | Reporting speaker | Distractor endpoint | Unsafe pronoun | Negation lost | Uncertainty lost | Hypothesis lost | Reporting lost | Temporal wrong | Question factualized | Quotation factualized | Incidental factualized | Metaphor factualized | Unsafe persistible FP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| B | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| C | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |

A0 recorded seven exact safe abstentions (PR-167--PR-173); C recorded PR-171 and PR-172; B did not detect a safe partial case at its selected threshold. Additional legacy partial cases preserve unresolved text even when the original oracle uses `null`, and are auditable in `failure_cases.json` rather than counted as wrong resolved endpoints.

## Selection

Applying the frozen order, A0 and the selected B/C configurations all clear both safety gates, have zero downstream false candidates, and have precision 1.0. The next criterion is endpoint-pair accuracy: B=0.9697, C=0.9615, and A0=0.9152. Therefore the prescribed order selects B at threshold 0.50 before recall and F1 are considered. B's 0.20 recall is a substantial coverage limitation and must remain visible; the frozen rule supplies no minimum-coverage gate. A0's perfect development recall also partly reflects that the corpus vocabulary is the explicitly frozen V1 vocabulary and is not a generalization claim.

**Recommendation: `B_SELECTED` for review before any separately approved integration checkpoint.** No automatic promotion or route integration is performed here.
