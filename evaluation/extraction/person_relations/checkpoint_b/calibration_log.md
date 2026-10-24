# Checkpoint B development calibration log

This log covers only the relation development corpus. No frozen final-evaluation artifact was read.

| Cases | Failure | Previous behavior | Change | Scope | Safety rationale |
|---|---|---|---|---|---|
| Unit coordination case; PR-174 | `ENDPOINT_COVERAGE_GAP` | Only the first coordinated object was emitted | Recognize a two-name coordinated object list as two binary candidates | Shared downstream | Expand only an explicit local list; do not infer identities |
| PR-040, PR-054, PR-068, PR-082 | `WRONG_ENDPOINT_B` | The modifier `criação` was selected as endpoint B | Skip the fixed modifier `criação de` before reading the explicit following endpoint | Shared downstream | Removes four wrong resolved endpoints without nearest-person selection |
| PR-013, PR-027, PR-175--PR-177, PR-180 | `TEMPORAL_SCOPE_WRONG` | A coordinated predicate without a repeated copula became `UNRESOLVED` | Carry already determined compositional guards only across explicit same-clause coordination | Shared downstream | Reuse is limited to an explicit coordinated relation and cannot cross a sentence |

No detector-specific downstream rule was introduced. Labels and threshold selection affect only B/C detection.
