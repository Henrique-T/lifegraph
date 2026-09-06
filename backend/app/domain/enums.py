from enum import StrEnum


class Origin(StrEnum):
    CONVERSATION = "CONVERSATION"
    REF = "REF"
    SYSTEM_INFERENCE = "SYSTEM_INFERENCE"


class VerificationStatus(StrEnum):
    DECLARED = "DECLARED"
    PROBABLE = "PROBABLE"
    CONFIRMED = "CONFIRMED"
    DIVERGENT = "DIVERGENT"
    UNVERIFIED = "UNVERIFIED"


class CivilEventType(StrEnum):
    NASCIMENTO = "nascimento"
    CASAMENTO = "casamento"
    OBITO = "obito"
    NATIMORTO = "natimorto"


class Speaker(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"


class TemporalPrecision(StrEnum):
    DAY = "DAY"
    MONTH = "MONTH"
    YEAR = "YEAR"
    INTERVAL = "INTERVAL"
    UNKNOWN = "UNKNOWN"
