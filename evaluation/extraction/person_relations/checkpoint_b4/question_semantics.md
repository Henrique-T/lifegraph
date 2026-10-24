# V1 interrogative relation semantics

An interrogative may produce a `RelationCandidate` because it contains useful
linguistic relation evidence. It never represents a direct asserted fact.

- The existing `epistemic_status = UNCERTAIN` represents the blocked speech act.
- No new relation ontology or claim status is introduced.
- Every question candidate must fail linguistic persistence eligibility.
- `Quem` is preserved as source text but has semantic target
  `UNRESOLVED_MENTION`; it is never a Person.
- Reporting, polarity, temporal scope, and endpoint semantics remain independent.

Metrics distinguish a legitimate blocked candidate
(`QUESTION_RELATION_CANDIDATE`) from an unsafe eligibility error
(`QUESTION_UNSAFE_PERSISTIBLE`). The deprecated `QUESTION_FACTUALIZED` label is
not used for correctly blocked candidates.
