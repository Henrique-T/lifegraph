"""Controlled vocabulary used by the LifeGraph domain model."""

from enum import StrEnum


class Origin(StrEnum):
    """Source from which a graph assertion originated."""
    CONVERSATION = "CONVERSATION"
    REF = "REF"
    SYSTEM_INFERENCE = "SYSTEM_INFERENCE"


class VerificationStatus(StrEnum):
    """Epistemic status assigned to a conversational claim."""
    DECLARED = "DECLARED"
    PROBABLE = "PROBABLE"
    CONFIRMED = "CONFIRMED"
    DIVERGENT = "DIVERGENT"
    UNVERIFIED = "UNVERIFIED"


class CivilEventType(StrEnum):
    """Civil event types supported by the current PoC."""
    NASCIMENTO = "nascimento"
    CASAMENTO = "casamento"
    OBITO = "obito"
    NATIMORTO = "natimorto"


class Speaker(StrEnum):
    """Allowed authors of conversation turns."""
    USER = "USER"
    SYSTEM = "SYSTEM"


class TemporalPrecision(StrEnum):
    """Precision levels supported by temporal intervals."""
    DAY = "DAY"
    MONTH = "MONTH"
    YEAR = "YEAR"
    INTERVAL = "INTERVAL"
    UNKNOWN = "UNKNOWN"
