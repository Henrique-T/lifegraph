# Checkpoint B.3 reporting mismatch audit

The B.2 `A0_B2` predictions contained seven matched candidates whose oracle was
`REPORTED` but whose predicted mode was `DIRECT`.

| Case | Construction | Expected | Actual | Polarity | Epistemic | Temporal | Persistence blocker |
|---|---|---|---|---|---|---|---|
| PR-286 | `Paulo contou a Renata, diante de Bruno e Clara, que João ...` | REPORTED | DIRECT | POSITIVE | ASSERTED | CURRENT_OR_UNSPECIFIED | reported mode itself |
| PR-287 | same reporting-verb complement family | REPORTED | DIRECT | POSITIVE | ASSERTED | CURRENT_OR_UNSPECIFIED | reported mode itself |
| PR-288 | same reporting-verb complement family | REPORTED | DIRECT | POSITIVE | ASSERTED | CURRENT_OR_UNSPECIFIED | reported mode itself |
| PR-289 | same reporting-verb complement family | REPORTED | DIRECT | POSITIVE | ASSERTED | CURRENT_OR_UNSPECIFIED | reported mode itself |
| PR-290 | same reporting-verb complement family | REPORTED | DIRECT | POSITIVE | ASSERTED | CURRENT_OR_UNSPECIFIED | reported mode itself |
| PR-291 | same reporting-verb complement family | REPORTED | DIRECT | POSITIVE | ASSERTED | CURRENT_OR_UNSPECIFIED | reported mode itself |
| PR-292 | same reporting-verb complement family | REPORTED | DIRECT | POSITIVE | ASSERTED | CURRENT_OR_UNSPECIFIED | reported mode itself |

## General failure family

The B.2 guard required `que` immediately after the reporting verb. An explicit
indirect object and parenthetical listener context between `contou` and `que`
therefore hid an otherwise unambiguous reported proposition.

## General correction

Within one sentence, a named source and a supported reporting verb may contain
an explicit complement or parenthetical context before `que`. Sentence and
semicolon boundaries remain hard scope limits. Supported verbs are finite.
Source introductions `segundo <Person>,` and `de acordo com <Person>,` are also
reported only when a person-shaped source and comma boundary are both present.
No rule is keyed to a case identifier.
