# LifeGraph Conversacional

The approved non-persistent extraction and explicit acceptance workflow is documented
in [docs/extraction-review-acceptance.md](docs/extraction-review-acceptance.md).
The minimal browser review workflow is documented in
[docs/review-ui.md](docs/review-ui.md).
Deliberate deterministic reconciliation controls are documented in
[docs/reconciliation-ui.md](docs/reconciliation-ui.md).

## Purpose

LifeGraph Conversacional turns fictional civil-life narratives into an auditable temporal graph. Narrative information is not registral fact: the application must preserve provenance and verification state so that user declarations, system inferences, and structured evidence remain distinguishable.

REF is an external source of structured registral evidence. It remains an independent deployment and its relational schema is not part of LifeGraph.

## Current milestone

Extraction review and acceptance milestone. **AI OUTPUT IS UNTRUSTED INPUT TO
LIFEGRAPH.** Extraction and review are non-persistent; only an individually
identified, explicit acceptance can persist a conversational declaration.

Implemented:

- FastAPI health and readiness endpoints;
- Neo4j Community persistence, constraints, and indexes;
- `Person`, `ConversationTurn`, `ClaimEvent`, `RefEvent`, and `Evidence` nodes;
- approved explicit graph relationships;
- validated origin, verification status, event type, and speaker enums;
- normalized read-only `GET /graph` endpoint;
- React/Vite frontend with the Cytoscape.js dependency;
- frontend node and edge counts;
- independent Docker Compose topology;
- approved `LIFEGRAPH_PT_CIVIL_V1` candidate pipeline (frozen B + S1C);
- expiring in-memory extraction reviews and explicit per-candidate accept/reject;
- idempotent accepted-candidate persistence with immutable AI provenance;
- unit, graph integration, and safety-invariant tests.
- read-only REF client for `GET /pessoas/{id_pessoa}/trilha`;
- explicit one-to-one `Person.external_ref_person_id` mapping;
- idempotent `RefEvent` import and `PARTICIPATES_IN` role preservation.
- timezone-aware claim intervals and canonical REF event/registration dates;
- deterministic, same-person reconciliation with explicit reason codes;
- idempotent reconciliation Evidence and narrowly refreshed engine results;
- explicit `SUPPORTED_BY` or `CONTRADICTS` edges only when justified by a rule;
- a separate CPU-only `fastino/gliner2.5-multi-v1` inference service;
- constrained extraction candidates with raw spans, offsets, and model scores;
- deterministic normalization of an isolated four-digit year into a candidate
  year interval;
- backend-to-model communication through `POST /extractions`;
- an external Hugging Face cache at `C:\AIModels\huggingface`.

Not implemented yet:

- graphical review UI for extraction candidates;
- Portuguese BERT, Gemma, or mREBEL models;
- complete temporal normalization or uncertainty detection;
- final extraction evaluation dataset;
- synthetic dataset generation;
- IBGE data collection;
- adaptive dialogue;
- Event Linker or probabilistic matching.

`ClaimEvent` and `RefEvent` are intentionally separate nodes. A `RefEvent`
existing in the same graph does not confirm a `ClaimEvent`. `SUPPORTED_BY` and
`CONTRADICTS` are created only through an explicit trusted persistence action;
node creation never creates either relationship or changes claim status.
Importing a REF event likewise does not confirm or compare a conversational
claim.

## AI extraction boundary

The GLiNER service receives text and returns a strict intermediate extraction
schema. It has no Neo4j driver or credentials, no REF URL or credentials, and
no Ollama configuration. It cannot create `Person`, `ConversationTurn`,
`ClaimEvent`, `Evidence`, or relationships; it cannot invoke reconciliation,
select an identity, query REF, or determine `CONFIRMED`/`DIVERGENT`.

The approved `LIFEGRAPH_PT_CIVIL_V1` pipeline combines the frozen
`B_LINGUISTIC_EVENT_SPANS` trigger detector with
`S1C_CONSERVATIVE_GUARDS`. Only `nascimento`, `casamento`, `obito`, and
`natimorto` candidates are allowed. Model confidence, when present, remains
metadata rather than a trust threshold. Uncertainty detection remains
unsupported.

The controlled Portuguese calibration procedure and low-memory service commands
are documented in [`docs/ai-experiment-procedure.md`](docs/ai-experiment-procedure.md).
Calibration accepts only immutable configuration IDs; callers cannot submit
arbitrary schema text. The subject-event experiments under
`evaluation/extraction/subject_association/` preserve the frozen historical
strategies and establish S1C as the approved conservative association stage.

Production `/extractions` creates only an expiring in-memory review. An
individual candidate is persisted only through its explicit `/accept` endpoint
with an existing `person_id`; accepted claims are always
`origin=CONVERSATION` and `verification_status=DECLARED`. Rejection is a graph
no-op, and acceptance never invokes REF or reconciliation.

## Deterministic reconciliation

Reconciliation is invoked explicitly with
`POST /claim-events/{claim_event_id}/reconcile`. Candidates are only same-type
`RefEvent` nodes connected to the same `Person`; the engine never performs a
global similarity search. It uses interval containment, not weighted scores or
arbitrary thresholds.

Current outcomes and reasons:

- no same-type event: `UNVERIFIED / NO_MATCHING_REF_EVENT_TYPE`;
- one dated event inside the claim interval: `CONFIRMED / EVENT_DATE_WITHIN_CLAIM_INTERVAL`;
- one dated event outside it: `DIVERGENT / EVENT_DATE_OUTSIDE_CLAIM_INTERVAL`;
- missing claim or REF event date: `UNVERIFIED / INSUFFICIENT_TEMPORAL_EVIDENCE`;
- exactly one compatible event among several: `CONFIRMED / UNIQUE_TEMPORALLY_COMPATIBLE_CANDIDATE`;
- several compatible events: `UNVERIFIED / AMBIGUOUS_MULTIPLE_REF_CANDIDATES`;
- no compatible event and every candidate has a known date: `DIVERGENT / NO_TEMPORALLY_COMPATIBLE_REF_EVENT`.

`PROBABLE` is not emitted by this version. Absence of REF evidence is not a
contradiction. No NLP date parsing, identity resolution, spouse/parent matching,
family coherence, or probabilistic scoring is implemented.

A year such as 2019 is supplied as the explicit interval from the beginning to
the end of 2019; it is never stored as an asserted January 1 date. Approximate
dates likewise require the caller to supply the intended interval.

Reconciliation changes only `verification_status` and its audit metadata. It
never changes `origin`, so both combinations below are valid:

```text
origin=CONVERSATION, verification_status=CONFIRMED
origin=CONVERSATION, verification_status=DIVERGENT
```

Generated `Evidence` is tagged `source=RECONCILIATION_ENGINE`, contains concise
rule outcomes rather than hidden reasoning, and is refreshed without touching
manual evidence or source nodes.

LifeGraph intentionally uses REF's canonical
`GET /pessoas/{id_pessoa}/trilha` endpoint because it is the person's civil
trajectory, restricted to principal roles and non-cancelled acts. The broader
`/eventos?id_pessoa=...` endpoint is not used as a timeline because it can
include secondary participation.

## Local architecture

```text
Browser
  |
  v
React/Vite :5173
  |
  v
FastAPI :8100
  |
  +----> Neo4j :7687 (:7474 Browser)
  |
  +---- GET only ----> External REF Backbone :8000
  |
  +----> GLiNER service :8200 (Compose network only)

REF remains an external, independent deployment.
```

`REF_BASE_URL` configures the external REF boundary. LifeGraph startup does not
depend on REF availability.

Application-owned identifiers are UUID v4 strings. The application generates
timezone-aware UTC `created_at` values and stores their ISO 8601 representation
in Neo4j.

## Ports

| Component | Local endpoint |
|---|---|
| Frontend | `http://127.0.0.1:5173` |
| API | `http://127.0.0.1:8100` |
| Neo4j Browser | `http://127.0.0.1:7474` |
| Neo4j Bolt | `bolt://127.0.0.1:7687` |
| External REF Backbone | `http://127.0.0.1:8000` |
| External REF PostgreSQL | `127.0.0.1:55432` |

## Running

PowerShell:

```powershell
Copy-Item .env.example .env
docker compose config
docker compose up --build -d
docker compose ps
```

Open `http://localhost:5173`. API documentation is available at `http://localhost:8100/docs`.

## Tests

```powershell
docker compose run --rm --no-deps backend pytest
docker compose run --rm --no-deps gliner pytest
```

The integration tests require the running Neo4j service and clean up only the
UUIDs that they create.

The live REF test is opt-in. Supply `REF_BEARER_TOKEN` and
`LIVE_REF_PERSON_ID` only to that test container; the production REF client
still performs only `GET /pessoas/{id_pessoa}/trilha`.

## Stopping

```powershell
docker compose down
```

The Neo4j named volume is preserved. Removing it requires the explicit destructive command `docker compose down -v`, which is not part of the normal workflow.

## Configuration

Copy `.env.example` to the ignored `.env` file and replace its local demonstration password. Configuration is environment-driven:

- `APP_ENV`
- `API_HOST`
- `API_PORT`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `REF_BASE_URL`
- `REF_BEARER_TOKEN` (required only for imports; never commit a real token)
- `OLLAMA_BASE_URL` (future only)
- `GLINER_BASE_URL` (internal model-service URL)
- `GLINER_TIMEOUT_SECONDS`

`host.docker.internal` reaches services published by the Windows host. REF and
Ollama are not contacted during LifeGraph startup.

## Model storage

Model binaries must not be stored in this OneDrive repository. The GLiNER
container uses the external cache root below; future models must remain outside
the repository too:

```text
C:\AIModels
C:\AIModels\huggingface
C:\AIModels\ollama
```
