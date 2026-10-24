# LifeGraph Person-Relation Checkpoint B.1 Characterization

## Methodological boundary

This development pass uses 313 synthetic narratives and 284 expected candidates from the two prior development corpora plus a separate 133-case generalization expansion. It does not use the frozen final evaluation. A0 was not calibrated: the historical lexical baseline, B-specific labels, C-generic label, shared deterministic downstream pipeline, and bounded thresholds were retained.

The historical result remains `B_SELECTED_BY_ORIGINAL_CHECKPOINT_B_ORDER`. B.1 adds coverage as a prerequisite and makes no production selection.

## Integrity and oracle findings

Both prior corpora are strict UTF-8 with no stored mojibake or U+FFFD; the earlier visual corruption was console-only. PR-018 was the sole confirmed reviewed oracle contradiction: `nunca foi mãe de` now retains `PAST`, consistently with PR-133 and PR-137. It remains negated and non-persistible.

## Selected development configurations

| Strategy | Threshold | Safety pass | Persistible recall | End-to-end recall |
|---|---:|---:|---:|---:|
| A0_ORIGINAL | 1.00 | no | 0.6142 | 0.8028 |
| B | 0.70 | yes | 0.0551 | 0.0810 |
| C | 0.20 | no | 0.0787 | 0.1127 |

B's threshold rose from 0.50 to 0.70 because lower thresholds produced unsafe persistible candidates on the expanded corpus. C has no threshold in the bounded grid with zero unsafe persistible false positives; at 0.30 it also produced two wrong resolved endpoints.

## Principal findings

- A0 remains precise on the original explicit vocabulary, but its B.1 generalization recall is 0.5294 and its persistible-oracle recall on the new cases is 0.2222. It entirely misses reordered, appositive, contracted-preposition, existential/have, and discontinuous forms.
- A0 factualizes seven emphatic-negation variants and five new uncertainty variants as linguistically eligible, producing 12 unsafe persistible false positives. It is therefore rejected before coverage ranking.
- B is the only selected configuration satisfying both hard safety gates, but misses 261 of 284 candidates and recovers only 7 of 127 persistible-oracle candidates correctly. Its coverage is not minimally useful.
- C misses 252 candidates and produces one unsafe persistible false positive. No evaluated C threshold passes the safety gate.
- All strategies have zero downstream false relation candidates on no-relation controls because the shared deterministic normalizer rejects unsupported model detections. Raw GLiNER detector false-positive counts remain high.
- No wrong resolved endpoints occur in the selected configurations. Silence is not mistaken for safety because total misses, persistible recall, and unnecessary abstention are reported separately.

## Abstention

A0 records 28 safe abstentions and seven unnecessary abstentions; B records two and two; C records four and one, respectively. Rates are conditioned on matched partial/resolvable candidates, while total misses are reported separately. The separation prevents a detector that misses a candidate entirely from being credited as a safe abstention.

## Coverage decision

Policy R4 requires persistible-oracle recall >= 0.50, every relation type >= 0.30, and every positive critical phenomenon family >= 0.20 after both safety gates pass. No strategy satisfies the complete protocol.

`PRODUCTION_SELECTION = NO_STRATEGY_PASSES_COVERAGE_GATE`

No detector was integrated into routes, review, persistence, Neo4j, UI, or REF.
