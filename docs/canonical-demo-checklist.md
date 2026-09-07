# LifeGraph canonical demo checklist

## Before recording

- [ ] Use a prepared and preserved Neo4j demo volume.
- [ ] Confirm that `neo4j`, `gliner`, `backend`, and `frontend` are running.
- [ ] Confirm that Neo4j and GLiNER are healthy before opening the interface.
- [ ] Open `http://localhost:5173` and confirm an HTTP 200 response.
- [ ] Set the browser to 100% zoom in a 1080p desktop viewport.
- [ ] Confirm that the synthetic **Reconciliation Demo** Person exists.
- [ ] Confirm that the imported marriage/2019 RefEvent exists in LifeGraph.
- [ ] Do not start or depend on live REF HTTP during the presentation.

## Expected sequence

- [ ] Load: “Nasci em 1988, casei em 2010 e me casei novamente em 2019.”
- [ ] Select **Extrair narrativa** manually.
- [ ] Verify three candidates: birth/1988, marriage/2010, and marriage/2019.
- [ ] Explicitly select **Reconciliation Demo** for each candidate.
- [ ] Accept each candidate individually as a declaration.
- [ ] Pause and show all three ClaimEvents as `CONVERSATION + DECLARED`.
- [ ] Reconcile each ClaimEvent individually.
- [ ] Verify birth/1988 → `UNVERIFIED`.
- [ ] Verify marriage/2010 → `DIVERGENT`.
- [ ] Verify marriage/2019 → `CONFIRMED`.
- [ ] Show the deterministic reasons, RefEvent, and unchanged `CONVERSATION` origin.

## Safety and replay

- [ ] Explain that an AI candidate, accepted declaration, and confirmed fact are distinct states.
- [ ] Explain that `UNVERIFIED` does not mean false.
- [ ] Explain that `DIVERGENT` is relative to the civil-registry evidence currently available.
- [ ] Do not use bulk actions or automatic reconciliation.
- [ ] Respect `ONE_RUN_PER_DATASET`: accepting a new run creates new claims.
- [ ] To replay the demo, restore a clean copy of the prepared volume; never use
      `docker compose down -v` as a routine replay mechanism.
