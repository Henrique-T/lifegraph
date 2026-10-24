# Person-Relation V1 architecture snapshot

```text
Narrative
   │
   ▼
Frozen deterministic extraction
LIFEGRAPH_PERSON_RELATION_V1 · A0_B2+B3+B4
   │
   ▼
RelationCandidate (linguistic interpretation, no Person identity)
   │
   ▼
Human review ── grounded corrections only
   │
   ▼
Explicit existing Person A + Person B selection
   │
   ▼
Authoritative eligibility
   ├── NEGATED ─────────── BLOCKED
   ├── UNCERTAIN ───────── BLOCKED
   ├── HYPOTHETICAL ────── BLOCKED
   ├── REPORTED ────────── BLOCKED
   ├── PAST/UNRESOLVED ─── BLOCKED
   ├── partial/unbound ─── BLOCKED
   ├── same Person ─────── BLOCKED
   ├── ungrounded ──────── BLOCKED
   ├── QUESTION ────────── BLOCKED
   └── eligible + accepted
              │
              ▼
RelationClaim
origin=CONVERSATION · verification_status=DECLARED
              │
              ▼
Neo4j provenance graph
  ├── ENDPOINT_A → Person
  ├── ENDPOINT_B → Person
  └── EXTRACTED_FROM → ConversationTurn
```

The graph contains claims, not direct factual kinship edges. Canonical pair keys group structure but never deduplicate independent declarations. No inverse claim, Person creation, name binding, narrator binding, GLiNER fallback, event-derived relation, REF comparison, or relation reconciliation occurs in V1.

Temporary reviews live in one backend process for 30 minutes. ConversationTurn is created when review opens; rejected, expired, restarted, or abandoned reviews can therefore leave an unreferenced turn. Persisted claims and their provenance survive restart in Neo4j.
