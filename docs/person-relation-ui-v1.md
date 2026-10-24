# Person-Relation V1 UI

Checkpoint C3 exposes the frozen `LIFEGRAPH_PERSON_RELATION_V1` workflow without changing extraction, review, eligibility, or persistence semantics.

## Workflow and terminology

The UI separates event candidates from relation candidates. A relation card is labelled **RELAÇÃO · interpretação automática**. Extraction does not assert truth. Acceptance records a human review decision. Persistence creates a first-class `RelationClaim` whose immutable server-controlled status is `DECLARED` and origin is `CONVERSATION`; it does not confirm a fact.

Each relation candidate displays its relation type and Portuguese label, grounded relation surface, endpoint mentions and semantic targets, polarity, epistemic status, reporting mode, temporal scope, review state, and the server's eligibility blocker.

## Explicit Person binding

Endpoint A and endpoint B each use a selector populated only from `GET /persons`. Both start empty. The UI performs no exact-name or fuzzy matching, creates no Person, and never preselects a narrator identity. `NARRATOR_ROLE` is visibly identified but must still be bound by the reviewer to an existing Person. `UNRESOLVED_MENTION` remains visible; selecting a Person does not erase the linguistic blocker.

## Corrections

The correction panel exposes only C1-approved changes: relation type, half-open relation and endpoint spans, and a grounded endpoint-role swap. Text is always derived from the immutable narrative at the selected offsets and is validated again by the backend. Polarity, epistemic status, reporting mode, temporal scope, origin, verification status, and extraction provenance are not editable.

## Eligibility and questions

The backend is authoritative. The UI renders `ELIGÍVEL` or `BLOQUEADA` and a Portuguese explanation of `primary_blocker`. Question candidates remain inspectable and reviewable, but cannot reach an enabled persistence action because C1 keeps them ineligible. Negated, uncertain, hypothetical, reported, historical, unresolved, unbound, same-Person, and ungrounded candidates likewise show their blocker rather than disappearing.

## Review lifecycle

- `PENDING` can be submitted for acceptance or rejected.
- A blocked acceptance renders `BLOCKED` and its server reason.
- `ACCEPTED_FOR_PERSISTENCE` plus `eligible=true` exposes **Persistir declaração**.
- `REJECTED` is terminal and disables accept/persist controls.
- `PERSISTED` shows the RelationClaim ID, `CONVERSATION`, and `DECLARED`.
- A repeated persistence response is shown as the existing claim, not a second success artifact.
- HTTP 404/410 is presented as: “Esta revisão expirou. Execute a extração novamente.” Browser state is never used to reconstruct an expired review.

## Graph representation

Relation claims are rendered as a distinct, text-labelled node:

```text
(RelationClaim)-[:ENDPOINT_A]->(Person A)
               -[:ENDPOINT_B]->(Person B)
               -[:EXTRACTED_FROM]->(ConversationTurn)
```

The UI never synthesizes a direct Person-to-Person kinship edge and never collapses RelationClaim nodes by `canonical_pair_key`. Selecting a RelationClaim shows claim ID, relation type, origin, verification status, both endpoint Persons, source narrative and ConversationTurn, accepted and original surfaces, correction flag, pipeline/configuration provenance, review/candidate IDs, structural family, and canonical pair key.

## Demonstration narratives

- `João é pai de Maria.` — bind two existing Persons, accept, persist, and inspect a `DECLARED` RelationClaim.
- `João não é pai de Maria.` — visible `NEGATED` candidate; persistence blocked.
- `João é pai de Maria?` — visible question mention; persistence blocked.
- `João é meu pai.` — `NARRATOR_ROLE` is visible and requires explicit binding.
- `João é pai de Maria e irmão de Pedro.` — independent cards, bindings, decisions, and persistence operations.

Event-only wording remains event-only. The relation UI does not derive `SPOUSE_OF` from `João se casou com Maria em 2019.`
