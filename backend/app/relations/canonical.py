"""Pure structural canonicalization for person relations."""

from app.relations.enums import CanonicalRelationFamily, RelationType


def canonical_relation_family(relation_type: RelationType) -> CanonicalRelationFamily:
    """Map a declared relation type to its structural grouping family."""

    if relation_type in {
        RelationType.FATHER_OF,
        RelationType.MOTHER_OF,
        RelationType.SON_OF,
        RelationType.DAUGHTER_OF,
    }:
        return CanonicalRelationFamily.PARENT_CHILD
    if relation_type in {RelationType.BROTHER_OF, RelationType.SISTER_OF}:
        return CanonicalRelationFamily.SIBLING
    return CanonicalRelationFamily.SPOUSE


def canonical_pair_key(
    relation_type: RelationType,
    endpoint_a_person_id: str,
    endpoint_b_person_id: str,
) -> str:
    """Return grouping metadata without collapsing independent claims.

    Parent-child pairs are oriented parent first. Sibling and spouse pairs are
    sorted because their structural grouping is symmetric. The key is not a
    uniqueness constraint and does not generate an inverse claim.
    """

    family = canonical_relation_family(relation_type)
    if family is CanonicalRelationFamily.PARENT_CHILD:
        if relation_type in {RelationType.SON_OF, RelationType.DAUGHTER_OF}:
            first, second = endpoint_b_person_id, endpoint_a_person_id
        else:
            first, second = endpoint_a_person_id, endpoint_b_person_id
    else:
        first, second = sorted((endpoint_a_person_id, endpoint_b_person_id))
    return f"{family.value}:{first}:{second}"
