# Canonical guided demo

This 2–3 minute demonstration uses only synthetic LifeGraph data and RefEvents
already imported into Neo4j. REF HTTP is not required.

## Start

```powershell
docker compose up -d neo4j gliner backend frontend
```

Open `http://localhost:5173` and choose **Carregar narrativa de demonstração**.
The button only prefills this text:

> Nasci em 1988, casei em 2010 e me casei novamente em 2019.

## Guided actions

1. Select **Extrair narrativa**. Expect nascimento/1988, casamento/2010, and
   casamento/2019, all with narrator as subject.
2. Inspect each AI candidate. For each one, explicitly select the existing
   synthetic Person **Reconciliation Demo** and choose **Aceitar como declaração**.
3. Pause at the graph: all three new ClaimEvents must be `CONVERSATION + DECLARED`.
   Acceptance must not reconcile them.
4. Select each ClaimEvent and choose **Reconciliar com evidência registral** once.
5. Show the expected results:
   - nascimento/1988: `UNVERIFIED`, because no nascimento RefEvent is connected;
   - casamento/2010: `DIVERGENT`, because the available casamento RefEvent is in 2019;
   - casamento/2019: `CONFIRMED`, with `SUPPORTED_BY` to the 2019 RefEvent.
6. Open deterministic reasons and registral provenance. Emphasize that every
   claim keeps `origin = CONVERSATION`.

## Interpretation

```text
AI candidate != accepted declaration != registral confirmation
```

`UNVERIFIED` means insufficient evidence, not false. `DIVERGENT` means the claim
diverges from available registral evidence, not that the narrator acted
maliciously. `CONFIRMED` means the conversational claim is supported; it does
not change its origin to REF.

The 2010 marriage result does not mean that LifeGraph assumes a person can have
only one marriage. It means only that this declaration is incompatible with the
registral evidence currently imported and available for the selected Person
under the deterministic same-person, same-event-type, and temporal comparison
rules. This demonstration illustrates provenance and uncertainty handling; it
does not assert a complete civil biography.

## Replay policy

Version 1 is intentionally **one run per Neo4j dataset**. Extraction sessions and
candidate IDs are runtime-generated, so rerunning acceptance would create new
claims. Before a presentation, use a preserved clean demo volume or a fresh
copy of that volume. No cleanup command is supplied because deleting by names,
text, or inferred ownership would be unsafe. Never use `docker compose down -v`
for routine replay.

The manifest at `demo/lifegraph_demo_manifest.json` records stable prerequisites
and expected outcomes. It performs no actions and contains no secrets.
