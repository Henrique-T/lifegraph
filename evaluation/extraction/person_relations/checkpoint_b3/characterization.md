# LifeGraph Person-Relation Checkpoint B.3 Characterization

## Decision

`NOT_READY_FOR_REVIEW_INTEGRATION`

The frozen deterministic configuration retained zero wrong resolved endpoints,
zero unsafe persistible false positives, zero reporting-mode losses, and zero
narrator-role errors. It passed R4 on the existing combined development corpus
and the B.2 challenge split.

The one-shot B.3 unseen corpus failed R4 because the appositional-relative family
had 0/2 recovery. The two misses are B3-U-008 and B3-U-009. No extraction or
oracle change was made after observing them.

Two questions (B3-U-034 and B3-U-036) produced non-persistible candidates. The
epistemic question guard prevented either from becoming an unsafe persistible
false positive, but they remain `QUESTION_FACTUALIZED` precision failures.

## Reporting readiness

The seven original B.2 mismatches (PR-286 through PR-292) belonged to reporting
verbs with explicit listener/context material before `que`. The sentence-local
family rule now handles them. Named source introductions using `segundo` and
`de acordo com` are also supported. Reporting does not cross a period or
semicolon. `REPORTED_MODE_LOST` is zero on existing, B.2 challenge, and B.3
unseen evaluations.

## Narrator readiness

Narrator-relative possessives use `NARRATOR_ROLE`, preserving the exact source
token and span. No graph Person field exists in the extraction schema. All 8
unseen narrator targets were represented correctly.

## One-shot attestation

1. Extraction code and reporting/narrator tests were completed.
2. Known development and B.2 challenge evaluation passed safety and R4.
3. The unseen oracle was generated and structurally validated.
4. SHA-256 `1b371b9a58c59899836cd7f8fd4535ddfeaf4793f4f8c0106a173fa7a5278ec9`
   was recorded before prediction.
5. The unseen prediction was executed once.
6. Extraction code and unseen oracle were not changed afterward.

The next extraction checkpoint must decide whether appositional relative clauses
and question suppression belong in the frozen V1 supported family set. Review or
binding integration should not begin before that decision and validation.
