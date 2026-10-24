# Person-Relation V1 checkpoint manifest

| Checkpoint | Purpose | Main decision | Safety outcome | Previously committed? |
|---|---|---|---|---|
| A | Runtime schemas and frozen specification | Seven relation types, canonical families, deterministic eligibility | No same-Person, unknown node, automatic binding, past persistence, free-text correction, REF, or event-derived relation | Yes, at `27caa6d` |
| B | Initial extraction characterization | Compare lexical A0 and GLiNER B/C under shared downstream logic | Hard wrong-endpoint and unsafe-persistence metrics introduced | No; consolidated by C4 |
| B.1 | Generalization and methodology correction | Add diverse corpus and R4 coverage gate | Low-coverage abstention can no longer win selection | No; consolidated by C4 |
| B.2 | Structural extraction improvement | Select deterministic `A0_B2`; GLiNER unsupported as primary | Safety plus tuning/challenge R4 passed | No; consolidated by C4 |
| B.3 | Reporting, narrator, unseen readiness | Explicit narrator linguistic role; reporting semantics frozen | No narrator graph autobinding; reporting loss reduced to zero | No; consolidated by C4 |
| B.4 | Relative apposition and questions | Questions may be candidates but never factual claims; extraction frozen | `LIFEGRAPH_PERSON_RELATION_V1`, hash `32040A…FC7D` | No; consolidated by C4 |
| C1 | Temporary review and Person binding | Two explicit existing-Person selections; grounded corrections | Eligibility remains server-authoritative; no graph write | No; consolidated by C4 |
| C2 | RelationClaim persistence | First-class DECLARED claim with endpoint/provenance edges | Atomic/idempotent; no factual Person edge or cross-turn collapse | No; consolidated by C4 |
| C3 | UI and graph visualization | Separate relation review surface and first-class claim visualization | Blockers and DECLARED status visible; no client autobinding | No; consolidated by C4 |
| C4 | Demo and release readiness | Reproducible fixture, reset, real-service smoke, docs, controlled checkpoint | Frozen semantics validated and relation-only commit allowlisted | This checkpoint |

Checkpoint B’s historical selection ordering and B.1’s `NO_STRATEGY_PASSES_COVERAGE_GATE` remain preserved in their artifacts. The final extraction choice is the B.2–B.4 deterministic structural pipeline, without GLiNER primary or fallback relation detection.
