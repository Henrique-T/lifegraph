# LifeGraph Person-Relation Checkpoint B.2 Characterization

## Method

Checkpoint B.2 freezes a deterministic 228/85 tuning/challenge split of the existing 313 development narratives. It introduces no new corpus cases. Structural and safety changes are implemented by linguistic family in an isolated module and are not reachable from application routes.

## Result

A0_B2 passes both hard safety gates and all R4 components on tuning, challenge, and combined development data. Combined relation precision/recall/F1 are 1.0000/0.9155/0.9559; persistible-oracle recall is 0.9055; the minimum type recall is 0.8205; and the minimum positive critical-phenomenon recall is 0.5000. Challenge persistible-oracle recall is 0.9630, with zero wrong endpoints and zero unsafe persistible false positives.

B_B2, C_B2, and D1 pass the safety gates at their selected thresholds because the common structural layer filters unsupported evidence, but all fail R4 coverage. D1 does not improve GLiNER span quality or coverage.

The historical states remain unchanged:

- Checkpoint B: `B_SELECTED_BY_ORIGINAL_CHECKPOINT_B_ORDER`;
- Checkpoint B.1: `NO_STRATEGY_PASSES_COVERAGE_GATE`;
- Checkpoint B.2: `PRODUCTION_SELECTION = A0_B2`.

This selection is a recommendation for a later integration checkpoint. No route, review flow, Person binding, RelationClaim persistence, graph, UI, or REF behavior changed.
