# Checkpoint B.1 Coverage Gate Analysis

Safety remains a prerequisite: a configuration with any wrong resolved endpoint or unsafe persistible false positive is rejected before coverage is considered.

| Policy | Conditions | A0 original | B | C |
|---|---|---:|---:|---:|
| R1 | Global end-to-end recall >= 0.50 | pass | fail | fail |
| R2 | Persistible-oracle recall >= 0.50 | pass | fail | fail |
| R3 | R2 and every relation type >= 0.30 | pass | fail | fail |
| R4 | R3 and every positive critical phenomenon family >= 0.20 | fail | fail | fail |

R4 is recommended as a deliberately minimal usability gate. Recovering fewer than half of safely persistible declarations would make the detector operationally sparse; the 30% type floor prevents a globally acceptable score from hiding an effectively unsupported V1 type; and the 20% phenomenon floor prevents complete blindness to a critical positive syntax. These are lower bounds, not target performance, and were applied uniformly after observing the empirical distributions rather than fitted to preserve a preferred detector.

A0 passes R1--R3 but fails R4 because reordered and appositive assertions have zero recovery. It also fails the prior safety step. B is the only selected configuration to pass both safety gates, but its persistible-oracle recall is 0.0551. C fails safety and coverage. Therefore no strategy reaches the production-selection stage.
