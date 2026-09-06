# S1C conservative safety-guard calibration

`S1C_CONSERVATIVE_GUARDS` is a calibration-only deterministic extension of the
frozen `S1B_PORTUGUESE_CONTINUITY` strategy. It is not used by the production
`/extractions` endpoint and never persists extraction output.

## Frozen experiment

- Model revision: `aaecfe45db1d828c963717054ccb868e8ad1f1d5`
- Original benchmark: `B79B5AC8CC7A5AB0F7CF4CBF18B5F42D96F8E4B625CC34AA7F87FBB4429102CA`
- V2 benchmark: `8B044F591760CAEA0042AA2E39B362073D0B1DB99D8248B5B846677E2E22C373`
- V3 benchmark: `B91C51586C638A8C7A47E268C341BF8E6107BA4708BB58019E721714B282A325`
- Stage-1 B semantic hash: `5B6B6F9317E92D2349287093E56415FDD50C11C4000428AF321D396747B85EF6`
- S1 AST hash: `F304FAA1A6C4ADB13AE6B11F86C3FB059DD34E6A36806D788F8B09DA0EC1754D`
- S1B AST hash: `D6F44078EE6F039176D9E7839328A57959FF22A9D8A9213C6DF9C02DCE0799B4`
- S1C AST hash: `5FE4A82626C19307D8669F36CFDDD30EF44F37C64006E69D1604BAAF707DBE6F`

The primary run was repeated in full after fixing a metrics-only bug that had
counted `UNRESOLVED/null` as an exact subject match. No strategy, benchmark, or
model definition was changed.

## Deterministic safeguards

S1C uses a five-verb reporting whitelist (`disse`, `contou`, `afirmou`, `falou`,
`declarou`) and the complementizer `que` to exclude people belonging to the
reporting clause. It excludes pre-trigger people locally governed by `com`,
`para`, or `sobre`, reconstructs adjacent possessive/article plus kinship nouns,
and abstains when plural event morphology and visible coordination indicate that
a single extracted person would be incomplete.

Guarded assignments emit machine-readable reason/warning codes. Conflicting or
insufficient evidence produces `UNRESOLVED`; no missing subject defaults to the
narrator.

## Primary result

Wrong resolved subjects (`wrong / resolved`):

- Original: S1 `4/19`, S1B `4/27`, S1C `1/26`
- V2: S1 `6/24`, S1B `6/41`, S1C `0/39`
- V3: S1 `15/28`, S1B `15/30`, S1C `0/20`

On V3, S1C produced zero reporting-person leakage, zero incidental-person
leakage, zero unsafe coordinated-subject reductions, and zero false narrator
attributions. Coverage intentionally fell because unsafe resolutions became
abstentions.

These results support presenting S1C output in a future explicit review layer.
They do not authorize automatic ClaimEvent creation, verification, or
reconciliation.
