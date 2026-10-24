# Checkpoint B.1 Calibration Log

## Corpus and oracle changes

- PR-018: corrected `temporal_scope` from `CURRENT_OR_UNSPECIFIED` to `PAST` after comparison with PR-133, PR-137, PR-096, and PR-124. The change affects only the development oracle and preserves its non-persistible status.
- PR-181--PR-313: added as a separate generalization corpus. Each case targets a named linguistic or safety phenomenon rather than an observed frozen-evaluation example.

## Extraction changes

None. A0, B, C, the shared normalizer, endpoint association, and linguistic guards remain exactly as implemented in Checkpoint B. This preserves `A0_ORIGINAL` and prevents silent corpus-specific rule expansion.
