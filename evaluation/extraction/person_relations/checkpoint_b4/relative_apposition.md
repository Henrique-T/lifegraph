# Relative-clause apposition

The supported deterministic family is:

`HEAD_PERSON, que [local modifier] COPULA RELATION COMPLEMENT, ...`

Supported local modifiers include explicit negation and `talvez`; supported
copulas cover current, past, and subjunctive forms already used by V1. Contracted
`da` and `do` complements retain their existing normalization.

Endpoint A is the explicit head. Endpoint B is the local complement. A closing
comma is mandatory. The rule does not cross arbitrary nested clauses.

When the relative clause contains a reporting proposition, such as `João, que
disse que Pedro é pai de Maria, ...`, the ordinary inner predicate produces
`FATHER_OF(Pedro, Maria)` with reported mode. João is not inherited as endpoint.

Nominal appositions nested inside an open relative clause are conservatively
abstained because attachment would require a general parser.
