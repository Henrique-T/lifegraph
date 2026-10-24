"""Closed vocabularies for conversational person relations."""

from enum import StrEnum


class RelationType(StrEnum):
    """Person-relation types supported by V1."""

    FATHER_OF = "FATHER_OF"
    MOTHER_OF = "MOTHER_OF"
    SON_OF = "SON_OF"
    DAUGHTER_OF = "DAUGHTER_OF"
    BROTHER_OF = "BROTHER_OF"
    SISTER_OF = "SISTER_OF"
    SPOUSE_OF = "SPOUSE_OF"


class RelationPolarity(StrEnum):
    """Whether the relation is asserted positively or negated."""

    POSITIVE = "POSITIVE"
    NEGATED = "NEGATED"


class EpistemicStatus(StrEnum):
    """Epistemic qualification expressed by the narrative."""

    ASSERTED = "ASSERTED"
    UNCERTAIN = "UNCERTAIN"
    HYPOTHETICAL = "HYPOTHETICAL"


class ReportingMode(StrEnum):
    """Whether the narrator states or reports the relation."""

    DIRECT = "DIRECT"
    REPORTED = "REPORTED"


class RelationTemporalScope(StrEnum):
    """Temporal interpretation supported by V1 relation candidates."""

    CURRENT_OR_UNSPECIFIED = "CURRENT_OR_UNSPECIFIED"
    PAST = "PAST"
    UNRESOLVED = "UNRESOLVED"


class EndpointMentionResolution(StrEnum):
    """Resolution state of a linguistic endpoint mention."""

    RESOLVED_MENTION = "RESOLVED_MENTION"
    UNRESOLVED_MENTION = "UNRESOLVED_MENTION"


class EndpointSemanticTarget(StrEnum):
    """Linguistic endpoint kind, deliberately separate from graph identity."""

    EXPLICIT_MENTION = "EXPLICIT_MENTION"
    NARRATOR_ROLE = "NARRATOR_ROLE"
    UNRESOLVED_MENTION = "UNRESOLVED_MENTION"


class CanonicalRelationFamily(StrEnum):
    """Structural family used only for grouping relation claims."""

    PARENT_CHILD = "PARENT_CHILD"
    SIBLING = "SIBLING"
    SPOUSE = "SPOUSE"


class PersistenceEligibility(StrEnum):
    """Deterministic V1 persistence result and blocking reasons."""

    PERSISTIBLE = "PERSISTIBLE"
    NOT_PERSISTIBLE_PARTIAL_ENDPOINT = "NOT_PERSISTIBLE_PARTIAL_ENDPOINT"
    NOT_PERSISTIBLE_NEGATED = "NOT_PERSISTIBLE_NEGATED"
    NOT_PERSISTIBLE_UNCERTAIN = "NOT_PERSISTIBLE_UNCERTAIN"
    NOT_PERSISTIBLE_HYPOTHETICAL = "NOT_PERSISTIBLE_HYPOTHETICAL"
    NOT_PERSISTIBLE_REPORTED = "NOT_PERSISTIBLE_REPORTED"
    NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE = (
        "NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE"
    )
    NOT_PERSISTIBLE_UNBOUND_ENDPOINT = "NOT_PERSISTIBLE_UNBOUND_ENDPOINT"
    NOT_PERSISTIBLE_SAME_PERSON_ENDPOINTS = (
        "NOT_PERSISTIBLE_SAME_PERSON_ENDPOINTS"
    )
    NOT_PERSISTIBLE_UNGROUNDED_CORRECTION = (
        "NOT_PERSISTIBLE_UNGROUNDED_CORRECTION"
    )
    NOT_PERSISTIBLE_NOT_ACCEPTED = "NOT_PERSISTIBLE_NOT_ACCEPTED"
