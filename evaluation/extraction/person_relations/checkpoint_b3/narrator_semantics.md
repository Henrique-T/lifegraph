# Narrator-relative endpoint semantics

`NARRATOR_ROLE` is a linguistic endpoint target, not a graph identity.

- `João é meu pai` is `FATHER_OF(João, NARRATOR_ROLE)`.
- `Meu pai é João` has the same declared direction.
- The exact possessive token (`meu` or `minha`, preserving source case and span)
  remains endpoint provenance.
- `EXPLICIT_MENTION`, `NARRATOR_ROLE`, and `UNRESOLVED_MENTION` are distinct.
- No Person ID, placeholder Person, narrator UUID, or current-user binding is
  present in `RelationCandidate`.
- Persistence still requires later reviewer binding of both endpoints to two
  existing and distinct Person nodes.

Narrator role does not license cross-sentence coreference and is not equivalent
to an indefinite expression such as `uma pessoa`, `alguém`, or `um pai`.
