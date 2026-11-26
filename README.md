# LifeGraph Conversacional

LifeGraph Conversacional is a proof of concept that transforms Portuguese civil-life narratives into an auditable temporal graph. It extracts candidate events, requires explicit human review before persistence, and compares accepted declarations with separately imported civil-registration evidence. A plausible narrative or AI extraction never becomes a fact automatically.

## Purpose

The project investigates how incomplete, informal, or ambiguous civil-life narratives can be represented without losing provenance—the origin and processing history of information—or uncertainty. It keeps conversational declarations, system processing, and structured REF evidence distinct so users can inspect what was stated, what the model extracted, and what the available civil-registration evidence supports.

REF is the external civil-registry system used as LifeGraph's source of structured registration evidence. It remains an independent application, and its relational database schema is not part of LifeGraph.

## Running

Copy the example configuration to the ignored local environment file, replace the demonstration password, validate the Compose configuration, and start the services:

**Powershell**:
```powershell
Copy-Item .env.example .env
New-Item -ItemType Directory -Force C:\AIModels\huggingface
docker compose config
docker compose up --build -d
docker compose ps
```

Wait until `backend`, `frontend`, `gliner`, and `neo4j` are running, then check
`http://localhost:8100/ready`. Open `http://localhost:5173`. API documentation
is available at `http://localhost:8100/docs`. If startup fails, inspect the
service with `docker compose logs <service>`; the first GLiNER build and model
download may take several minutes.

Configuration is environment-driven:

- `APP_ENV`, `API_HOST`, and `API_PORT` configure the API;
- `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` configure graph access;
- `REF_BASE_URL` and `REF_BEARER_TOKEN` configure explicit REF imports;
- `GLINER_BASE_URL` and `GLINER_TIMEOUT_SECONDS` configure extraction;
- `OLLAMA_BASE_URL` is reserved for future experimental use.

Never commit the local `.env` or a real REF token. `host.docker.internal` reaches services published by the Windows host. REF and Ollama are not contacted during LifeGraph startup.

## Ports

| Component | Local endpoint |
|---|---|
| Frontend | `http://127.0.0.1:5173` |
| API | `http://127.0.0.1:8100` |
| Neo4j Browser | `http://127.0.0.1:7474` |
| Neo4j Bolt | `bolt://127.0.0.1:7687` |
| External REF Backbone | `http://127.0.0.1:8000` |
| External REF PostgreSQL | `127.0.0.1:55432` |

## Stopping

```powershell
docker compose down
```

The Neo4j named volume is preserved. `docker compose down -v` also removes that volume and is intentionally not part of the normal workflow.

## Tests

```powershell
docker compose exec -T backend python -m pytest -q
docker compose run --rm --no-deps gliner python -m pytest -q
python -m pytest frontend/tests -q
docker compose exec -T frontend npm run build
```

Graph integration tests require Neo4j, the graph database used by LifeGraph, and clean up only the UUID identifiers they create. The live REF test is opt-in and requires `REF_BEARER_TOKEN` and `LIVE_REF_PERSON_ID` only in its test environment.

The frozen final evaluation has its own protocol and authorization boundary in
[`docs/experimental-evaluation-protocol.md`](docs/experimental-evaluation-protocol.md).
Do not use its reserved dataset for routine development testing or tuning.

## Architecture

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

The main flow is shown below. A `ClaimEvent` is an accepted conversational declaration; a `RefEvent` is a separate civil-registration event imported from REF.

```text
Narrative -> extraction candidate -> human review -> explicit Person selection
          -> accepted ClaimEvent (CONVERSATION / DECLARED)
          -> explicit reconciliation against imported RefEvents
          -> CONFIRMED, DIVERGENT, or UNVERIFIED
```

Extraction and review do not write to the graph. Rejection creates no claim. Acceptance writes a `ClaimEvent`; REF import writes a separate `RefEvent`; reconciliation is a later explicit operation. Application-owned identifiers are UUID v4 strings, and timestamps are stored as timezone-aware ISO 8601 values.

The browser provides one narrative input that coordinates two specialized paths. Events use GLiNER plus deterministic subject-association guards. Explicit family relations use a separate deterministic structural extractor. Both groups appear in the same review stage, but relation acceptance remains distinct from explicit `RelationClaim` persistence. The graph can also be consulted independently by selecting an existing Person and switching between the relational view and that Person's chronological civil-event timeline.

Person search only filters existing graph nodes; it never binds an identity automatically. Relation claims require two explicit selections and remain `CONVERSATION / DECLARED`, with `ENDPOINT_A`, `ENDPOINT_B`, and `EXTRACTED_FROM` edges rather than a factual Person-to-Person kinship edge. Relation claims are not reconciled against REF.

The supported relation types are `FATHER_OF` (pai de), `MOTHER_OF` (mãe de), `SON_OF` (filho de), `DAUGHTER_OF` (filha de), `BROTHER_OF` (irmão de), `SISTER_OF` (irmã de), and `SPOUSE_OF` (cônjuge de).

## AI extraction boundary

The GLiNER service, which uses a span-based named-entity extraction model, receives text and returns a strict intermediate schema. It has no Neo4j or REF credentials and cannot create graph nodes, select an identity, invoke reconciliation, or assign a final verification state.

The approved extraction pipeline combines a linguistic civil-event trigger detector with deterministic, conservative subject-association safety guards. Only `nascimento`, `casamento`, `obito`, and `natimorto` candidates are permitted. Model confidence remains metadata rather than a trust threshold.

Production extraction creates an expiring in-memory review. A candidate is persisted only through its explicit acceptance endpoint with an existing `person_id`. Accepted claims always use `origin=CONVERSATION` and `verification_status=DECLARED`.

## Deterministic reconciliation

Reconciliation is invoked explicitly with `POST /claim-events/{claim_event_id}/reconcile`. Candidate evidence is limited to same-type `RefEvent` nodes connected to the same `Person`. The engine uses temporal interval rules rather than similarity, embeddings, or probabilistic scoring.

Current outcomes include:

- `CONFIRMED` when compatible imported evidence is deterministically identified;
- `DIVERGENT` when the declaration conflicts with currently available dated evidence under the rules;
- `UNVERIFIED` when evidence is absent, insufficient, or ambiguous.

`UNVERIFIED` does not mean false, and `DIVERGENT` does not imply deception. Reconciliation changes `verification_status`, never `origin`. Generated `Evidence` stores concise rule outcomes and machine-readable identifiers for the rules that produced them.

LifeGraph imports the civil trail exposed by REF through `GET /pessoas/{id_pessoa}/trilha`. Identity linkage is explicit; the PoC does not search people by similarity or infer identities probabilistically.

LifeGraph development/evaluation datasets and controlled demo fixtures are synthetic. The external REF initial load contains real civil-registry records; imported REF data must therefore be treated as potentially identifiable and sensitive. The current PoC does not provide production-grade governance or LGPD compliance controls.

## Model storage

Model binaries must remain outside this OneDrive repository. The GLiNER container uses an external cache:

```text
C:\AIModels
C:\AIModels\huggingface
C:\AIModels\ollama
```

These directories are local caches, not project files. A new developer must create `C:\AIModels\huggingface`; on the first GLiNER startup, the model is downloaded from Hugging Face into that directory. The first startup therefore takes longer and requires network access and sufficient disk space. Later starts reuse the cached files. Without network access or a pre-populated cache, the GLiNER service cannot become ready and narrative extraction remains unavailable, although the remaining application services can still run.

## Documentation

The canonical controlled demo material is described by [`demo/lifegraph_demo_manifest.json`](demo/lifegraph_demo_manifest.json). The relation workflow and its safety boundaries are documented in [`docs/person-relations.md`](docs/person-relations.md); no additional fixture-loading command is implied by these files.

- [Extraction, review, and acceptance contract](docs/extraction-review-acceptance.md)
- [Person-relation workflow](docs/person-relations.md)
- [Reconciliation UI](docs/reconciliation-ui.md)
- [AI experiment procedure](docs/ai-experiment-procedure.md)
- [Conservative subject-association safety guards](docs/subject-association-safety-guards.md)
- [Formal experimental evaluation protocol](docs/experimental-evaluation-protocol.md)
