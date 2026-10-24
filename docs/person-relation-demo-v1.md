# Person-Relation V1 demo

This is a local PoC demonstration. Persisted relations are conversational declarations (`DECLARED`), not confirmed facts.

## Prerequisites and startup

1. Docker Desktop with Compose.
2. Copy `.env.example` to `.env` and set a non-empty local `NEO4J_PASSWORD`.
3. Keep the approved model cache at `C:/AIModels/huggingface` for the existing event extractor.
4. Start the stack from the repository root:

```powershell
docker compose up --build -d
docker compose ps
```

Services and checks:

| Service | Port | Check |
|---|---:|---|
| Neo4j HTTP/Bolt | 7474 / 7687 | Compose healthcheck |
| GLiNER/event extraction | 8200 internal | `docker compose exec gliner python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8200/ready').read().decode())"` |
| Backend | 8100 | `GET http://localhost:8100/health` and `/ready` |
| Frontend | 5173 | `http://localhost:5173` |

Compose starts Neo4j first, then the backend after Neo4j is healthy. The frontend waits for backend health. The deterministic relation endpoint is hosted by the extraction service but does not use GLiNER inference; GLiNER remains required for the existing event workflow.

## Deterministic fixture

The fixture creates only four marked synthetic Persons and no RelationClaims:

```powershell
docker compose exec backend python scripts/person_relation_demo.py seed
```

| Display name | Stable ID |
|---|---|
| João | `demo-person-rel-v1-joao` |
| Maria | `demo-person-rel-v1-maria` |
| Pedro | `demo-person-rel-v1-pedro` |
| Ana | `demo-person-rel-v1-ana` |

## Three-minute flow

### Positive declaration

1. Open the relation section and enter `João é pai de Maria.`
2. Extract. Expect `FATHER_OF`, endpoint A `João`, endpoint B `Maria`, with both selectors empty.
3. Select the fixture João and Maria explicitly.
4. Accept. Expect `ACCEPTED_FOR_PERSISTENCE`.
5. Select **Persistir declaração**. Expect a RelationClaim ID, `CONVERSATION`, and `DECLARED`.
6. Refresh/select the claim in the graph. Expect one RelationClaim with `ENDPOINT_A`, `ENDPOINT_B`, and `EXTRACTED_FROM`; there is no direct Person-to-Person kinship edge.

### Safety controls

- `João não é pai de Maria.`: `NEGATED`, blocked, no persistence action, graph unchanged.
- `João é pai de Maria?`: question mention visible, blocked, graph unchanged.
- `João é meu pai.`: endpoint B is `NARRATOR_ROLE`; nothing is preselected. Explicitly bind both existing Persons before acceptance.

### Provenance and duplicates

Repeat the positive flow in a new extraction session. The graph intentionally contains two RelationClaim nodes with different claim IDs and ConversationTurns; their canonical pair key may match. Repeating **persist** for the same accepted review returns the existing claim idempotently.

## Automated service smoke

With the stack running:

```powershell
docker compose exec backend python scripts/person_relation_demo.py smoke
```

This uses the real HTTP APIs and Neo4j to check positive persistence, replay, independent declarations, negation, questions, narrator semantics, three claim edges, and zero factual kinship edges.

## Reset

```powershell
docker compose exec backend python scripts/person_relation_demo.py reset
```

Reset removes only RelationClaims connected to the four reserved demo Person IDs, their now-unreferenced source turns, and isolated Persons with those exact IDs. It does not delete arbitrary Persons or all nodes by label. Unreferenced ConversationTurns from rejected, expired, restarted, or abandoned reviews cannot be safely identified by the frozen schema and may remain; inspect/remove them manually only with their exact review IDs.

## Restart and expiration

- Review TTL is 30 minutes.
- Backend restart discards temporary review state.
- A lost/expired review must be extracted and reviewed again; the browser cannot reconstruct acceptance.
- Persisted RelationClaims remain in Neo4j and survive backend restart.

## Expected screenshots

Capture: the relation card before binding; the accepted state; the persisted `DECLARED` result; the RelationClaim topology and provenance panel; one negated blocker; one question blocker; and the narrator endpoint with empty selector.

## Known limitations

Review storage is process-local and non-durable. Reviewer identity/authentication, persisted-claim editing/deletion, relation search/versioning, cleanup of abandoned review turns, REF reconciliation, and verified factual relations are future work.
