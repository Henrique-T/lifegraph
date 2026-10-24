# Person-Relation Review V1

Checkpoint C1 adds a temporary, server-side review workflow after the frozen
`LIFEGRAPH_PERSON_RELATION_V1` extractor. It does not persist a
`RelationClaim`, create graph relationships, or establish factual truth.

## Boundary and lifecycle

The flow is `RelationCandidate -> temporary review -> grounded corrections ->
two explicit Person bindings -> eligibility -> accepted-for-persistence or
rejected`. `ACCEPTED_FOR_PERSISTENCE` means that a later checkpoint may persist
the declaration; it does not mean persisted or verified.

Review sessions are held in process memory for 30 minutes, matching the event
review proof-of-concept. Restarting the backend invalidates them, and the store
is suitable only for a single worker. Each candidate is reviewed independently.
Its states are `PENDING`, `BLOCKED`, `ACCEPTED_FOR_PERSISTENCE`, `REJECTED`, and
`EXPIRED`. Accepted and rejected states are terminal. Replaying the identical
acceptance payload is idempotent; a different payload conflicts.

## Identity binding

Both endpoints require reviewer-selected IDs of existing LifeGraph `Person`
nodes. The backend checks both IDs with the graph repository. It never selects a
Person by name, creates a Person, consults REF, or writes a Person ID into the
immutable extraction candidate. The two IDs must differ.

`NARRATOR_ROLE` remains a linguistic endpoint, not the current user or
conversation owner. It requires the same explicit Person selection as an
ordinary mention. An `UNRESOLVED_MENTION` remains blocked unless review supplies
a grounded endpoint correction; a graph binding alone cannot resolve language.

## Corrections and provenance

The source narrative and original `RelationCandidate` are immutable. Review may
correct only the relation type and grounded relation/endpoint spans, may swap
endpoint roles using the original opposite spans, and may change an endpoint
semantic target when the corrected source text supports it.

Offsets are Python Unicode code-point indices in a half-open `[start, end)`
interval. Every correction must satisfy
`0 <= start < end <= len(source_text)` and
`source_text[start:end] == supplied_text`. Relation-type corrections must be the
deterministic normalization of the accepted relation surface. Arbitrary evidence
text and ungrounded endpoint creation are rejected.

Review cannot modify polarity, epistemic status, reporting mode, temporal scope,
interrogative blocking semantics, extraction provenance, origin, or verification
status. A wrong immutable semantic dimension requires rejection and a future
extractor-version change. Original and corrected values remain separately
auditable.

## Eligibility

The sole eligibility implementation is
`backend/app/relations/eligibility.py:evaluate_relation_persistence`. Its primary
blocker precedence is:

1. negated;
2. hypothetical;
3. uncertain (including questions);
4. reported;
5. partial linguistic endpoint;
6. unsupported temporal scope (`PAST` or `UNRESOLVED`);
7. unbound endpoint;
8. same-Person endpoints;
9. ungrounded correction;
10. reviewer not accepted;
11. persistible.

Person existence is an additional service-level prerequisite before this pure
predicate runs. Question candidates are reviewable but always blocked under V1.
No frontend state can override these server checks.

## API

- `POST /relation-extractions` accepts one immutable narrative and creates a
  temporary review session using extraction revision `A0_B2+B3+B4` and frozen
  configuration hash
  `32040A53D33F30A4DDDBA0E423180AB9DC08AF17B583BB6B3A9A82BEA091FC7D`.
- `GET /relation-reviews/{review_id}` returns the non-expired session.
- `POST /relation-reviews/{review_id}/candidates/{candidate_id}/accept` accepts
  two explicit Person IDs and optional grounded corrections.
- `POST /relation-reviews/{review_id}/candidates/{candidate_id}/reject` records a
  terminal temporary rejection.

Requests use strict schemas. Unknown fields—including `origin`,
`verification_status`, extraction provenance, semantic safety dimensions, or
Person-creation payloads—are rejected. Future claim constants remain
`origin=CONVERSATION` and `verification_status=DECLARED`, but clients cannot set
them.

## Persistence and security invariants

Both acceptance and rejection report zero graph-node and graph-edge deltas. C1
creates no `RelationClaim`, Person-to-Person edge, graph constraint, index, or
relation provenance edge. Unknown or expired reviews, unknown candidates,
unknown Persons, self-relations, mismatched spans, and invalid state transitions
are rejected deterministically. The frozen extractor contains no GLiNER primary
or fallback path, and existing event extraction/review contracts are unchanged.
