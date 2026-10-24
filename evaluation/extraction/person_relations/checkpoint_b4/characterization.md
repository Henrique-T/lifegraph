# Person-Relation Checkpoint B.4 Characterization

## Outcome

`READY_FOR_REVIEW_INTEGRATION`

The deterministic structural extractor now supports bounded relative-clause
apposition and freezes interrogatives as reviewable, non-persistible linguistic
candidates. No GLiNER primary or fallback path is present.

The previously seen B3-U-008 and B3-U-009 cases are recovered by the general
relative rule. B3-U-034 and B3-U-036 are correctly blocked question candidates;
they are not counted as factualization failures.

## Independent micro-challenge

The B.4 oracle contained 26 narratives and 20 candidates. It was validated and
sealed at SHA-256
`0e3a6fd000fc6b7730f63df222ecb4bef446a000d324cd9712569fc8237722de`
before prediction. The first prediction recovered all candidates with no false
relation, wrong endpoint, unsafe persistence, reporting loss, or narrator error.
Relative apposition recovered 8/8 and all seven question candidates were blocked.

No extraction code, guard, parser, configuration, or oracle was modified after
the one-shot micro-challenge prediction.

## Scope boundary

This readiness statement covers extraction only. Review API integration, endpoint
Person binding, RelationClaim persistence, graph writes, UI, and REF remain absent.
