# Minimal extraction review UI

Start only the required LifeGraph services:

```powershell
docker compose up -d neo4j gliner backend frontend
```

Open `http://localhost:5173`, enter a Portuguese narrative, and select
**Extrair narrativa**. Extraction is non-persistent. Each returned candidate
shows its trigger, conservatively associated subject, participants, date, and
whether the subject is `RESOLVED` or `UNRESOLVED`.

Acceptance always requires explicitly selecting an existing LifeGraph Person.
Neither `__NARRATOR__`, a third-party mention, nor an unresolved subject chooses
a Person automatically. Optional corrections remain visibly separate from the
original AI values. **Aceitar como declaração** persists only a
`CONVERSATION + DECLARED` ClaimEvent; **Rejeitar** is a graph no-op.

Reviews expire after approximately 30 minutes and are lost when the backend
restarts. If this happens, run extraction again; the browser never reconstructs
or resubmits an unrecognized candidate.

The graph reloads after acceptance and distinguishes Person, ClaimEvent,
RefEvent, ConversationTurn, and Evidence nodes by both text and color. Selecting
a ClaimEvent shows origin, verification status, trigger, pipeline, and correction
metadata.

```text
AI candidate != accepted conversational declaration != confirmed registral fact
```

The UI does not call REF and provides no reconciliation control.
