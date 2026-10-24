# Person-Relation Persistence V1

Checkpoint C2 persists an independently reviewed conversational declaration as a
first-class `RelationClaim`. Persistence records what was declared; it does not
confirm that declaration as factual.

## Graph representation

```text
(RelationClaim)-[:ENDPOINT_A]->(Person)
(RelationClaim)-[:ENDPOINT_B]->(Person)
(RelationClaim)-[:EXTRACTED_FROM]->(ConversationTurn)
```

The declared `relation_type` is a property of `RelationClaim`. C2 never creates
`FATHER_OF`, `SPOUSE_OF`, or another kinship edge directly between Persons. It
does not generate inverse or symmetric claims.

Every claim stores `origin=CONVERSATION` and
`verification_status=DECLARED`; clients cannot supply either value. It preserves
the immutable source, original and accepted evidence, endpoint semantic targets,
linguistic safety dimensions, frozen extraction provenance, explicit Person
bindings, review timestamps, canonical family, and canonical pair metadata.

## Source provenance

C1 did not previously retain an addressable graph turn. The smallest C2-required
extension creates or idempotently resolves a `ConversationTurn` when a relation
review is opened and stores its ID in the temporary review. The turn is keyed by
`review_extraction_id`, immutable source text, and `speaker=USER`. Persistence
requires that exact turn and source. A lost or expired in-memory review cannot be
reconstructed from client data even if its turn remains in the graph.

## Persistence command and state

`POST /relation-reviews/{review_id}/candidates/{candidate_id}/persist` accepts
only an empty JSON object. Relation type, Persons, evidence, provenance, origin,
and verification state all come from the accepted server-side review.

Review and persistence states are orthogonal:

- `review_status=ACCEPTED_FOR_PERSISTENCE` remains the human decision;
- `persistence_status=NOT_PERSISTED|PERSISTED` records materialization.

Pending, blocked, rejected, expired, unknown, or process-lost reviews cannot
persist. `PERSISTED` does not mean confirmed.

## Atomicity and idempotency

One Cypher statement first matches both distinct Persons and the exact source
turn, then merges the claim by `persistence_operation_key`, and creates all three
required edges. Neo4j executes this statement as one transaction: an error rolls
back the node and every edge.

The operation key is SHA-256 over the review ID, candidate ID, source turn,
accepted payload hash, effective candidate, explicit bindings, and frozen
extraction provenance. Replaying one accepted operation returns the existing
claim. A separate review produces a different operation key and claim even when
its relation type, endpoints, and `canonical_pair_key` match.

The only RelationClaim uniqueness constraints are:

- `RelationClaim.relation_claim_id`;
- `RelationClaim.persistence_operation_key`.

`canonical_pair_key` is not unique. It is grouping metadata and never collapses
independent declarations.

## Read model and safety boundary

The repository can read a complete claim only when `ENDPOINT_A`, `ENDPOINT_B`,
and `EXTRACTED_FROM` all exist. The generic graph response includes
`RelationClaim` nodes and these explicit edges, preserving the claim-node model.

C2 performs no REF lookup or reconciliation, adds no `SUPPORTED_BY` or
`CONTRADICTS` relation, assigns no status beyond `DECLARED`, creates no Person,
and performs no identity, narrator, inverse, or event-derived inference.

No authoritative reviewer identity currently exists. C2 therefore stores
`review_id`, `candidate_id`, `reviewed_at`, and `accepted_at` without fabricating
an identity. `REVIEWER_IDENTITY_AVAILABLE = NO`.
