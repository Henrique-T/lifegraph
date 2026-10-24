# Checkpoint B.1 Oracle Consistency Audit

The audit compared compositional fields in minimal or near-minimal constructions for current and past copulas, negation, uncertainty, reporting, questions, and endpoint completeness.

| Case A | Case B | Field | Linguistic reason | Verdict |
|---|---|---|---|---|
| PR-018 | PR-133 | `temporal_scope` | Both use `nunca foi mãe de`; only PR-133 recorded the past copula as `PAST`. | ORACLE_ERROR_CONFIRMED |
| PR-018 | PR-137 | `temporal_scope` | `nunca foi` consistently denotes past scope independently of relation type. | ORACLE_ERROR_CONFIRMED |
| PR-096 | PR-124 | `temporal_scope` | `foi marido de` and `era esposa de` are consistently `PAST`. | CONSISTENT |
| PR-004 | PR-132 | polarity and temporal scope | `não é pai de` is negated and current/unspecified in both cases. | CONSISTENT |
| PR-019 | PR-139 | epistemic status | `Talvez ... seja` is `UNCERTAIN` in both cases. | CONSISTENT |
| PR-007 | PR-146 | reporting mode | `disse que` is `REPORTED` and the speaker is not an endpoint. | CONSISTENT |
| PR-008 | PR-180 | reporting and epistemic status | Reporting and uncertainty remain compositional. | CONSISTENT |
| PR-171 | related pronoun cases | endpoint resolution | The pronoun remains a textual mention but is non-persistible without safe antecedent resolution. | CONSISTENT |

PR-018 was corrected from `CURRENT_OR_UNSPECIFIED` to `PAST`. Polarity remains `NEGATED`, and `persistible_in_v1` remains `false`. No other confirmed contradiction was found in the reviewed families.
