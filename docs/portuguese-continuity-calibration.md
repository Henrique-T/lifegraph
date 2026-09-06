# Portuguese subject continuity calibration

This experiment compares the historical `S1_DETERMINISTIC` association strategy with
`S1B_PORTUGUESE_CONTINUITY`. It does not change the production extraction endpoint.

## Frozen inputs

- Model revision: `aaecfe45db1d828c963717054ccb868e8ad1f1d5`
- Original benchmark SHA-256: `B79B5AC8CC7A5AB0F7CF4CBF18B5F42D96F8E4B625CC34AA7F87FBB4429102CA`
- Stage-1 B semantic SHA-256: `5B6B6F9317E92D2349287093E56415FDD50C11C4000428AF321D396747B85EF6`
- Historical S1 AST SHA-256: `F304FAA1A6C4ADB13AE6B11F86C3FB059DD34E6A36806D788F8B09DA0EC1754D`
- Adversarial benchmark SHA-256: `8B044F591760CAEA0042AA2E39B362073D0B1DB99D8248B5B846677E2E22C373`
- S1B rules AST SHA-256: `D6F44078EE6F039176D9E7839328A57959FF22A9D8A9213C6DF9C02DCE0799B4`

The primary comparison was run once after these artifacts were frozen. No post-hoc
rule or benchmark tuning is included in its results.

## S1B policy

S1B adds only two capabilities to S1:

1. It recognizes the whitelisted first-person event forms `nasci`, `casei`, and
   `me casei`. It never assigns the narrator for third-person forms such as `casou`.
2. It carries a resolved subject only to a later trigger in the same sentence when
   an explicit comma, `e`, or `depois` coordination is present and no new Stage-1
   person span intervenes. Periods, exclamation/question marks, semicolons, and
   colons block continuity.

Explicit narrator or person evidence overrides a carried subject. A missing or
ambiguous subject remains `UNRESOLVED`; there is no default-to-narrator rule.

Machine-readable reason codes are:

- `EXPLICIT_FIRST_PERSON_PRONOUN`
- `FIRST_PERSON_VERB_FORM`
- `EXPLICIT_PRETRIGGER_SUBJECT`
- `COORDINATED_SUBJECT_CONTINUITY`
- `EXPLICIT_SUBJECT_OVERRIDE`
- `NO_SAFE_SUBJECT_EVIDENCE`
- `SENTENCE_BOUNDARY`

## Reproduction

Use the GLiNER-only runtime. REF, Neo4j, backend, and frontend are not required.

```powershell
docker compose stop backend neo4j frontend
docker compose -f ..\ref\docker-compose.yml stop
docker compose up -d --no-deps gliner
docker compose exec -T gliner python /evaluation/extraction/subject_association/v2/run_continuity.py
```

The benchmark performs no graph writes, REF calls, reconciliation, or ClaimEvent
creation. Restore only the services that were running before the experiment using
`docker compose start`; never use `down -v` for profile switching.

## Result boundary

S1B materially improves coverage while preserving zero false narrator attribution
in these fixed datasets. It still inherits unsafe/wrong explicit subject spans from
Stage 1/S1 in reporting and embedded-clause cases. Therefore these results are
calibration evidence, not authorization for persistence or production promotion.
