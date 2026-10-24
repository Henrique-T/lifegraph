# Checkpoint B.2 Calibration Log

All changes are family-level. No case identifier, exact name pair, or challenge sentence appears in production extraction rules.

| Family | Tuning evidence | Old behavior | General change | Negative controls | Challenge impact | Safety rationale |
|---|---|---|---|---|---|---|
| Reordered copula | B.1 `reordered` family | No candidate | Parse role complement before copula and role-holder after copula | Incidental `o pai de X falou...` | Recall retained on challenge | Endpoints come from named structural roles, not proximity |
| Apposition | B.1 `apposition` | No candidate | Attach relation complement to the immediately preceding comma-delimited head | Incidental and quoted controls | Challenge apposition recovered | Ambiguous/non-delimited attachment abstains |
| Contracted preposition | `contracted_preposition` | Unsupported | Treat `da`/`do` as grammatical contraction while preserving surface | `dela`/`dele` handled separately | Challenge family recovered | No semantic type conversion |
| `ter ... como` | `existential_have` | No candidate | Assign the role-person as endpoint A and holder as endpoint B | `como um/uma` social comparison | Challenge cases recovered | Direction derives from construction |
| Discontinuous predicate | `discontinuous` | No candidate | Allow only three explicit `segundo ...` parentheticals | Conditional/denial parentheticals | Challenge cases recovered | Arbitrary intervening clauses abstain |
| Coordination/chains | `coordination`, `appositive_chain` | Partial | Expand only comma/apposition or terminal two-name coordination | Independent second clause | No endpoint leakage | No nearest-person propagation |
| Partial endpoints | Existing partial cases | Generic phrase truncated | Preserve full generic phrase and mark unresolved | Unknown-person controls | Wrong endpoints reduced to zero | No invented identity |
| Emphatic negation | `negation_variant` | Positive/eligible | Scope explicit emphatic markers within the sentence | Unrelated-clause controls | Zero unsafe persistible FP | Negation always blocks persistence |
| Uncertainty | `uncertainty_variant` | Some markers asserted | Add only explicitly approved uncertainty families | Assertive controls | Zero unsafe persistible FP | No enum expansion or debatable adverbs |
| Hypothesis/reporting | Existing compositional cases | Incomplete combinations | Preserve independent dimensions and add `supondo/caso` scope | Direct controls | Safety retained | One dimension cannot overwrite another |

An early structural pass produced 20 wrong resolved endpoints and 17 unsafe persistible candidates. The general fixes were: generic-endpoint precedence, explicit `criação de` modifier handling, independent-clause protection, possessive phrase preservation, and hypothetical-scope completion. The corrected pass reached zero for both safety metrics before the GLiNER experiment. No change was made after inspecting challenge-only failures.
