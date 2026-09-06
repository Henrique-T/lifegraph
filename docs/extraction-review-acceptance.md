# Extraction review and acceptance

LifeGraph uses the approved Portuguese candidate pipeline `LIFEGRAPH_PT_CIVIL_V1`:

1. frozen `B_LINGUISTIC_EVENT_SPANS` detects civil-event mentions;
2. frozen `S1C_CONSERVATIVE_GUARDS` associates subjects, participants, and dates conservatively.

AI output is untrusted candidate data. The three boundaries are intentionally separate:

- `POST /extractions` runs AI and creates only a temporary in-memory review;
- review and `reject` do not write to Neo4j;
- only an individual `accept` request writes a `ConversationTurn`, a `ClaimEvent`, `SUBJECT_OF`, and `EXTRACTED_FROM`.

An accepted candidate is always `origin=CONVERSATION` and
`verification_status=DECLARED`. Acceptance never calls REF, reconciliation, or creates
`SUPPORTED_BY`/`CONTRADICTS`.

## API workflow

```text
POST /extractions
GET  /extractions/{extraction_id}
POST /extractions/{extraction_id}/candidates/{candidate_id}/accept
POST /extractions/{extraction_id}/candidates/{candidate_id}/reject
```

Acceptance requires an existing LifeGraph `person_id`. It never infers identity from
`__NARRATOR__`, a name, a kinship phrase, or a REF identity. Third-party and
`UNRESOLVED` candidates therefore require the reviewer to create/select the proper
Person separately. No Person or participant Person is automatically created.

Corrections are sent only inside the `corrections` object and are stored separately
from the immutable original candidate metadata. `origin`, `verification_status`,
model revision, and pipeline provenance are forbidden request fields.

## Temporary state and idempotency

Pending reviews live in one backend process for 30 minutes. A restart invalidates
them; no Redis or review database is used. The caller cannot submit original candidate
JSON: the server resolves `extraction_id + candidate_id` against its own store.

Accepted candidates use the unique key `{extraction_id}:{candidate_id}` in Neo4j.
Repeating the same payload returns the existing result; different corrections or a
different Person return `409 ACCEPTED_CANDIDATE_CONFLICT`. Rejection is a non-persistent
acknowledgement and creates no graph audit object.

## Epistemic separation

```text
AI candidate != declared conversational claim != confirmed fact
```

Confirmation remains an explicit, later deterministic reconciliation operation.
