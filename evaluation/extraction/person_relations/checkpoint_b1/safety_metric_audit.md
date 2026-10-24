# Checkpoint B.1 Safety Metric Audit

The metric regression suite constructs six distinguishable outcomes:

| Fixture | Required observation |
|---|---|
| Correct candidate | Persistible-oracle recall increases. |
| Wrong concrete endpoint | `WRONG_RESOLVED_ENDPOINT` and unsafe persistible count increase. |
| Eligible candidate for blocked oracle | `UNSAFE_PERSISTIBLE_FALSE_POSITIVE` increases. |
| Safe partial abstention | Safe-abstention count/rate increase without wrong resolution. |
| Unnecessary abstention | Unnecessary-abstention count/rate increase. |
| Total miss | Coverage and recall decrease while wrong-endpoint remains zero. |

Thus a silent detector can retain zero wrong endpoints, but it receives zero persistible-oracle recall and an explicit total-miss count. Similarly, marking every endpoint unresolved increases unnecessary abstention where the oracle expects safe resolution. Safety gates cannot substitute for coverage gates.
