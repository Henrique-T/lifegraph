# Relation Candidate and Claim V1 Specification

## Status and boundary

This document specifies a future, controlled extension. It does not describe current production behavior. V1 recognizes only explicit person-relation language and never derives relations from civil events. REF, relation reconciliation, automatic Person creation, name-based identity selection, probabilistic linkage, coreference expansion, and production security controls are outside this round.

The epistemic boundary is unchanged: an extracted `RelationCandidate` is temporary AI output; an explicitly accepted `RelationClaim` records a conversational declaration; neither is automatically a fact.

## Current architecture and impact

| Current component | Current responsibility | Relation impact | Required future change |
|---|---|---|---|
| GLiNER extraction service | Produces civil-event candidates and conservative subject associations | Relation extraction must not alter the event pipeline | Add a separate relation extractor/output branch with its own versioned configuration |
| `PipelineCandidate` / `ReviewCandidate` | Event-only temporary candidate and review state | Expiration and review status are reusable concepts; event fields are not | Define separate `RelationCandidate` and relation review schemas |
| `ExtractionService` | Keeps reviews in memory; accept is the sole graph-write boundary | Lifecycle, idempotency, and no-write rejection can be reused | Add relation-specific accept/reject methods and eligibility checks without routing through `ClaimEventCreate` |
| Extraction API routes | Extract, read review, accept, and reject event candidates | A common review response may contain typed candidate collections | Add typed relation routes or typed candidate endpoints; never infer candidate kind from fields |
| `CandidateCard` | Reviews one event and binds one existing Person | A relation needs two independent bindings and different corrections | Add an explicitly typed `RelationCandidateCard`; do not overload event controls |
| Person selector | Searches and explicitly selects an existing LifeGraph Person | Safe to reuse twice | Require independent endpoint A and B selections; never preselect by mention text |
| `ClaimEvent` | Stores an accepted conversational civil-event declaration | Provenance concepts are shared, event semantics are not | Add first-class `RelationClaim`; do not add relation fields to `ClaimEvent` |
| `GraphRepository` | Persists allow-listed nodes/edges and normalizes graph reads | Transaction/idempotency patterns are reusable | Add a dedicated atomic relation-acceptance transaction and graph normalization entries |
| `ConversationTurn` | Preserves accepted narrative text and extraction identifier | Can source both claim kinds | Reuse `EXTRACTED_FROM` because its provenance meaning remains identical |
| Graph API and Cytoscape view | Return and display five allow-listed node types | Relation claims would otherwise be invisible | Add `RelationClaim`, endpoint edges, labels, filters, and provenance details |
| Reconciliation | Compares `ClaimEvent` with imported `RefEvent` | No V1 relation role | Keep relation claims completely outside reconciliation |
| Evaluation artifacts | Separate development data from frozen evaluation | Relation data must have its own development boundary | Keep this corpus explicitly DEVELOPMENT / ADVERSARIAL and outside final protocol artifacts |

## RelationCandidate

`RelationCandidate` belongs only to the temporary review layer. It may be incomplete and must never contain graph identities selected by the extractor.

| Field | Type | Semantics |
|---|---|---|
| `candidate_id` | UUID/string | Temporary server-issued identity scoped to one review |
| `source_turn_reference` | string | Temporary reference to the submitted narrative; a persisted turn does not yet exist |
| `relation_type` | V1 enum | `FATHER_OF`, `MOTHER_OF`, `SON_OF`, `DAUGHTER_OF`, `BROTHER_OF`, `SISTER_OF`, or `SPOUSE_OF` |
| `relation_surface_text` | string | Exact lexical relation expression, preserved independently of canonical type |
| `relation_span_start`, `relation_span_end` | non-negative integers | Half-open offsets of the relation expression in the narrative |
| `endpoint_a_mention`, `endpoint_b_mention` | string or null | Linguistic mentions only; null means unresolved, never an unknown Person |
| `endpoint_a_span`, `endpoint_b_span` | span or null | Half-open offsets for recoverable mentions |
| `endpoint_a_resolution_state`, `endpoint_b_resolution_state` | `RESOLVED_MENTION` or `UNRESOLVED_MENTION` | Whether linguistic evidence supports a mention; not graph identity resolution |
| `polarity` | enum | `POSITIVE` or `NEGATED` |
| `epistemic_status` | enum | `ASSERTED`, `UNCERTAIN`, or `HYPOTHETICAL` |
| `reporting_mode` | enum | `DIRECT` or `REPORTED` |
| `reporting_source_mention` | string or null | Optional exact speaker mention only when safely delimited; never a Person ID |
| `temporal_scope` | `CURRENT_OR_UNSPECIFIED`, `PAST`, or `UNRESOLVED` | Prevents past wording from silently becoming a current relation; V1 persists only current/unspecified scope |
| `model_id`, `model_revision`, `pipeline_id` | strings | Extraction provenance |
| `configuration_hash` | string | Immutable relation-extraction configuration identifier |
| `warnings` | list of strings | Inspectable safety conditions |
| `persistence_eligibility` | eligibility enum | Deterministic explanation of whether acceptance may proceed |

`reporting_source_mention` is optional because identifying the reporting mode is safety-critical, while resolving the speaker mention is not required for a relation claim. Candidate corrections may change relation type, surface boundaries, endpoint roles, and endpoint mentions, but corrections remain separate from original extraction values.

### Grounded review corrections

The source narrative is immutable. A reviewer may select another substring, expand or shrink a span, swap endpoint roles when justified, or correct the canonical relation type. The reviewer may not invent mention text, enter arbitrary evidence, create a missing person mention, or rewrite the narrative. Offsets use Python Unicode code-point indices serialized as integers and half-open intervals. Every corrected relation or endpoint span must satisfy:

```text
0 <= start < end <= len(source_text)
source_text[start:end] == corrected_surface_or_mention
```

The server must validate these conditions; client-side controls are only usability aids.

### Persistence eligibility

Eligibility is recomputed server-side and is never trusted from the client. A candidate is `PERSISTIBLE` only when all of the following hold:

1. `polarity = POSITIVE`;
2. `epistemic_status = ASSERTED`;
3. `reporting_mode = DIRECT`;
4. `temporal_scope = CURRENT_OR_UNSPECIFIED`;
5. both linguistic endpoints are resolved;
6. endpoint A is explicitly bound to an existing Person;
7. endpoint B is explicitly bound to an existing Person;
8. the two Person IDs are different;
9. the reviewer explicitly accepts the candidate;
10. every correction remains grounded in the immutable source narrative.

This is a backend/persistence predicate. Temporary review may contain missing, identical, or incorrect endpoint bindings, but no UI state can override the server gate. Evaluation returns the most specific blocking reason:

1. `NOT_PERSISTIBLE_NEGATED`;
2. `NOT_PERSISTIBLE_HYPOTHETICAL`;
3. `NOT_PERSISTIBLE_UNCERTAIN`;
4. `NOT_PERSISTIBLE_REPORTED`;
5. `NOT_PERSISTIBLE_PARTIAL_ENDPOINT`;
6. `NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE`;
7. `NOT_PERSISTIBLE_UNBOUND_ENDPOINT`;
8. `NOT_PERSISTIBLE_SAME_PERSON_ENDPOINTS`;
9. `NOT_PERSISTIBLE_UNGROUNDED_CORRECTION`;
10. `PERSISTIBLE`.

Questions are represented conservatively as `UNCERTAIN`. Quoted or merely mentioned relation sentences produce no candidate. A partial candidate remains reviewable but cannot create a placeholder Person or claim.

### Temporal scope

`CURRENT_OR_UNSPECIFIED` covers present wording or wording without an explicit historical qualifier. `PAST` preserves forms such as “foi marido de” and “era esposa de”. `UNRESOLVED` records unsafe temporal interpretation. All three may remain visible during review, but only `CURRENT_OR_UNSPECIFIED` is persistible in V1. V1 does not define `valid_from`/`valid_to`; therefore a past candidate cannot be stored as an apparently current RelationClaim.

Partial candidates likewise remain reviewable only. They use null/unresolved mention state and never create `Person("Unknown")`, a placeholder Person, or any synthetic graph identity.

## RelationClaim

`RelationClaim` is a first-class conversational claim node, intentionally separate from `ClaimEvent`.

| Field | Type | Semantics |
|---|---|---|
| `relation_claim_id` | UUID/string | Persisted claim identity |
| `relation_type` | V1 enum | Reviewer-accepted canonical type |
| `origin` | `CONVERSATION` | Immutable provenance |
| `verification_status` | `DECLARED` | V1 has no REF reconciliation |
| `created_at` | aware datetime | Acceptance time |
| `endpoint_a_person_id`, `endpoint_b_person_id` | existing Person IDs | Explicit reviewer bindings, never extractor output |
| `conversation_turn_id` | string | Persisted source narrative |
| `original_relation_surface_text` | string | Immutable extracted wording |
| `original_endpoint_a_mention`, `original_endpoint_b_mention` | strings | Immutable extracted mentions |
| `accepted_relation_surface_text` | string | Accepted or corrected wording |
| `accepted_endpoint_a_mention`, `accepted_endpoint_b_mention` | strings | Accepted or corrected mentions |
| `reviewer_correction_applied`, `reviewer_corrections_json` | boolean/string | Audit of explicit corrections |
| `extraction_id`, `candidate_id`, model/configuration fields | strings | Extraction and idempotency provenance |
| `acceptance_payload_hash` | string | Detects conflicting repeat acceptance |
| `canonical_relation_family`, `canonical_pair_key` | strings | Structural grouping metadata, never a uniqueness constraint across declarations |

`ClaimEvent` and `RelationClaim` share origin, declaration status, extraction provenance, explicit acceptance, idempotency, and `ConversationTurn` sourcing. They intentionally do not share event type, time interval, participants, reconciliation fields, or event-subject semantics.

## Graph design

Future nodes are `Person`, `RelationClaim`, and the existing `ConversationTurn`. One accepted relation is represented as:

```text
(RelationClaim)-[:ENDPOINT_A]->(Person)
(RelationClaim)-[:ENDPOINT_B]->(Person)
(RelationClaim)-[:EXTRACTED_FROM]->(ConversationTurn)
```

`ENDPOINT_A` and `ENDPOINT_B` preserve the accepted linguistic direction. `SUBJECT_OF` is not reused because it currently means that a Person is the subject of a civil event claim. The relation surface and original endpoint mentions remain on `RelationClaim`; therefore graph identities never replace linguistic provenance.

Acceptance creates one node only. It never expands `MOTHER_OF` into `SON_OF`/`DAUGHTER_OF`, or `SPOUSE_OF`/sibling claims into reverse nodes. Idempotency uses the extraction candidate and acceptance-payload identity for the same acceptance operation.

### Canonicalization and independent provenance

Each independently reviewed and accepted conversational declaration creates its own `RelationClaim`, even when another claim has the same endpoints and canonical type. Each node retains its own `ConversationTurn` and acceptance provenance. **Technical deduplication is not claim collapse.**

`canonical_pair_key` supports structural grouping, deterministic comparison, duplicate visualization, same-operation idempotency support, and identification of symmetric endpoint pairs. It is not a uniqueness constraint and must not block, merge, or erase an independently accepted claim.

For `SPOUSE_OF`, the pair key sorts the two Person IDs under the `SPOUSE` family. `BROTHER_OF` and `SISTER_OF` share a sorted `SIBLING` pair grouping: `BROTHER_OF(João, Maria)` and `SISTER_OF(Maria, João)` can therefore be structurally associated. Their relation types, endpoint directions, surface forms, claim nodes, and ConversationTurn provenance remain distinct. Neither form generates or prevents the other.

## API impact map

| Area | Proposed future change | Write boundary | Safety invariant |
|---|---|---|---|
| Extraction response | Return separately typed `event_candidates` and `relation_candidates` | No write | A relation cannot masquerade as an event |
| Relation review read | Include original fields, corrections, status, eligibility, and expiry | No write | Server owns candidate identity and original values |
| Correction | `PATCH` a temporary relation candidate or include corrections on acceptance | Temporary state only | Corrected spans must be exact substrings of the immutable narrative |
| Endpoint binding | Supply `endpoint_a_person_id` and `endpoint_b_person_id` | No graph write until accept | Both IDs must resolve to distinct existing Persons; no name lookup binding |
| Rejection | Relation-specific reject operation | No graph write | Rejection creates no `RelationClaim` or Person |
| Acceptance | Relation-specific accept endpoint | Atomic write of turn, claim, and three edges | Server recomputes eligibility and enforces explicit dual binding |
| Graph read | Normalize `RelationClaim`, `ENDPOINT_A`, and `ENDPOINT_B` | Read only | No direct factual Person-to-Person edge is synthesized |
| Eligibility feedback | Return one deterministic eligibility code plus warnings | No write | UI cannot override a blocking state |

No relation endpoint calls REF or reconciliation.

## UI impact map

The review page should keep one common review sequence while rendering explicitly typed cards. An event card remains unchanged. A relation card shows canonical type, exact surface phrase, endpoint mentions, polarity, epistemic status, reporting mode, endpoint mention states, temporal limitation, and a human-readable eligibility reason.

The reviewer may correct the relation type and grounded mention spans, swap endpoint roles when supported by the text, bind endpoint A and endpoint B independently to existing Persons, reject, or accept. Search results must not auto-select identities. Acceptance stays disabled for partial, negated, uncertain, hypothetical, reported, past, unbound, same-Person, or ungrounded candidates. The backend repeats every eligibility check. Original and corrected values remain visible. The graph should label the node as a declared relation and show both endpoint roles and the source narrative; it must not render a direct Person-to-Person factual edge.

## Corpus policy

`evaluation/extraction/person_relations/v1_adversarial.jsonl` is DEVELOPMENT / ADVERSARIAL data. It may guide V1 design and tuning, is not population-representative, contains no graph Person IDs, and is isolated from the frozen final extraction evaluation. Incidental nominal kinship, quotations, metaphors, and event-only formulations are conservative no-candidate cases. Past relations may be candidates but are not persistible until temporal validity is modeled.

## Risk matrix

| Risk | Example | Consequence | Proposed mitigation |
|---|---|---|---|
| Wrong endpoint direction | Swapping parent and child | Reverses declared meaning | Exact spans, endpoint-role display, dual reviewer binding, direction tests |
| Wrong relation type | `irmã de` mapped to `MOTHER_OF` | False semantics | Closed vocabulary, lexical oracle tests, explicit correction |
| False-positive relation | “como um irmão” | Metaphor becomes civil assertion | Negative corpus, assertive-pattern boundary, reject/no-write flow |
| Negation loss | “não é pai” | Opposite claim persisted | Compositional polarity and server-side eligibility gate |
| Uncertainty loss | “talvez seja mãe” | Speculation factualized | Separate epistemic status and non-persistibility |
| Reported-speech factualization | “Pedro disse que...” | Third-party report becomes direct declaration | Reporting mode and optional source mention; block V1 persistence |
| Partial endpoint persistence | “filho de alguém” | Placeholder or invented identity | Dual resolved mentions and dual existing-Person binding required |
| Accidental identity resolution | Mention `Ana` selects a graph node | Wrong citizen linked | Never return Person IDs from extraction; explicit independent selectors |
| Self-relation persistence | Both endpoints bind to one Person | Structurally invalid claim | Backend rejects equal Person IDs with a deterministic eligibility code |
| Symmetric duplication | Two spouse directions | Duplicate semantic claim | One accepted node, no automatic inverse, deterministic pair metadata |
| Inverse duplication | Mother claim automatically creates child claim | Unsupported extra declaration | Preserve declared form only; never materialize inverse claims |
| Relation/event conflation | Marriage event becomes spouse relation | Scope and temporal errors | Separate candidates, schemas, services, nodes, and tests |
| Future REF overreach | Registral event treated as relation proof | Unsupported verification | No V1 REF path; require a separate future protocol |

## Proposed implementation checkpoints

| Checkpoint | Likely production files | Required tests | Acceptance gate | Rollback/safety concern |
|---|---|---|---|---|
| A. Schemas only | Separate backend/GLiNER schema modules and frontend types | Closed enums, strict fields, eligibility unit tests | Existing event JSON unchanged | Remove isolated relation schemas without migration |
| B. Candidate extraction | New relation extractor/configuration module | Corpus category tests and false-positive tests | No graph writes; safety errors remain zero | Feature flag disables relation branch |
| C. Review state | Extraction service or separate relation review service | Expiry, correction, rejection, idempotency tests | Rejection and review are graph no-ops | Disable relation reviews independently |
| D. Endpoint binding | Relation acceptance request/service | Unknown IDs, equal IDs, grounded corrections, no auto-selection tests | Two explicit, distinct, existing Person IDs required | No persistence migration yet |
| E. RelationClaim persistence | Domain schemas and graph repository | Atomicity, provenance, retry/conflict, no inverse tests | One claim plus endpoint/source edges only | Remove new node/edges from isolated test database |
| F. Graph normalization | Graph read schemas/repository | Allow-list and no direct Person edge tests | Existing graph response remains backward compatible | Hide new types behind response version/feature flag |
| G. UI | Typed card, API client, graph view | Component states, keyboard labels, disabled acceptance tests | Ineligible states cannot invoke acceptance | Feature flag hides relation UI |
| H. End-to-end adversarial tests | Test fixtures and integration tests | Full 120-case corpus plus persistence boundary subset | Zero unsafe accepted claims | Stop rollout; do not weaken oracle |
| I. Optional event-derived V2 | Separate future design only | New frozen development protocol | Explicit project approval required | Must not enter V1 code path |

## Remaining decisions before implementation

No unresolved product or scientific decision blocks Checkpoint A (schemas). Runtime representation details must follow the predicates above without weakening them.
