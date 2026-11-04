# Person relations

LifeGraph recognizes seven explicitly stated family relations:
`FATHER_OF`, `MOTHER_OF`, `SON_OF`, `DAUGHTER_OF`, `BROTHER_OF`,
`SISTER_OF`, and `SPOUSE_OF`. Relation extraction is deterministic and
structural; it is separate from the GLiNER event extractor and never derives a
family relation from a civil event.

## Workflow

One narrative submission starts the event and relation extraction paths. Their
results appear in separate groups in the same review stage.

```text
Narrative
  -> RelationCandidate (temporary linguistic interpretation)
  -> human review
  -> explicit selection of two existing Persons
  -> server-side eligibility decision
  -> acceptance for persistence
  -> explicit persistence
  -> RelationClaim (CONVERSATION / DECLARED)
```

Extraction never supplies graph Person IDs. Searching by name only filters
existing Persons; the reviewer must select each endpoint explicitly. A narrator
role is linguistic evidence, not an authenticated identity, and is never bound
automatically. The two endpoints must exist and must be different.

Reviews are held in one backend process for 30 minutes. A backend restart or
expiration invalidates them. The client cannot reconstruct a review from a
candidate payload, and accepted review state alone does not write a
`RelationClaim`.

## Eligibility and corrections

The backend is authoritative. Persistence is blocked for negated, uncertain,
hypothetical, reported, past, temporally unresolved, linguistically incomplete,
unbound, same-Person, ungrounded, rejected, or non-accepted candidates.
Questions remain reviewable but cannot be persisted as factual declarations.

The backend supports corrections grounded in exact source substrings and keeps
original and accepted evidence separately. The simplified interface exposes the
relation interpretation and explicit Person bindings but does not expose every
advanced offset-correction control. Polarity, epistemic status, reporting mode,
temporal scope, origin, verification status, and extraction provenance remain
server-controlled.

## API

```text
POST /relation-extractions
GET  /relation-reviews/{review_id}
POST /relation-reviews/{review_id}/candidates/{candidate_id}/accept
POST /relation-reviews/{review_id}/candidates/{candidate_id}/reject
POST /relation-reviews/{review_id}/candidates/{candidate_id}/persist
```

Persistence accepts no client-defined graph identity, origin, status, or
provenance fields. Replaying the same accepted operation is idempotent. A new
review of an equivalent declaration creates an independent claim with its own
source provenance.

## Graph representation

```text
(RelationClaim)-[:ENDPOINT_A]->(Person)
(RelationClaim)-[:ENDPOINT_B]->(Person)
(RelationClaim)-[:EXTRACTED_FROM]->(ConversationTurn)
```

Every persisted claim has `origin=CONVERSATION` and
`verification_status=DECLARED`. Persistence records a reviewed declaration; it
does not confirm the relation as true. LifeGraph creates no direct factual
kinship edge between Persons, no inverse or symmetric claim, and no Person.

Relation claims are not reconciled with REF. They also are not inferred from
events. The graph view preserves independent declarations instead of collapsing
them by relation type or endpoint pair.

## Current interface

The interface displays Portuguese relation labels, keeps event and relation
cards visually distinct, requires both Person selections, exposes blocking
reasons, and separates acceptance from persistence. Internal enum values and
technical identifiers are not emphasized in routine success messages. The
independent graph consultation can be opened without submitting a narrative and
offers a relational view and a chronological civil-event timeline for the
selected Person.

## Limitations

- The deterministic grammar is deliberately narrow and is not a general
  Portuguese relation extractor.
- Review state is process-local and non-durable.
- Abandoned reviews may leave unreferenced `ConversationTurn` nodes.
- There is no authoritative reviewer identity or automatic identity resolution.
- Persisted relation claims have no edit, version, delete, or REF reconciliation
  workflow.
- Browser behavior has been validated manually, but there is no automated
  browser end-to-end suite.
