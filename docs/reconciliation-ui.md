# Deliberate reconciliation UI

The graph provenance panel exposes reconciliation only when a `ClaimEvent` is
selected. The action **Reconciliar com evidência registral** invokes the existing
deterministic endpoint once per explicit click and then reloads `GET /graph`.

Reconciliation uses only `RefEvent` nodes already imported into LifeGraph and
connected to the same Person. The UI neither calls live REF HTTP nor imports REF
data, resolves identities, chooses an ambiguous candidate, or changes matching
rules.

The interface keeps origin and verification separate. For example:

```text
origin = CONVERSATION
verification_status = CONFIRMED
```

This means registral evidence supports a conversational declaration; it does not
mean the declaration originated in REF. `DECLARED` means accepted but not yet
reconciled. `UNVERIFIED` means reconciliation ran and available evidence was
insufficient. `PROBABLE` is reserved and is not emitted by the current engine.

Results include human-readable deterministic reasons, raw reason codes, matched
REF event details, considered candidate IDs, and persisted Evidence visible in
the graph. No reconciliation runs on extraction, acceptance, graph selection, or
opening the provenance panel.
