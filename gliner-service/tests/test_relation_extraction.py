"""Unit tests for the isolated Person-Relation V1 development pipeline."""

import pytest

from app.relation_extraction import (
    build_candidates,
    detect_a0,
    extract_relations,
    normalize_relation_span,
)
from app.relation_schemas import RelationDetection


@pytest.mark.parametrize(
    ("text", "relation_type", "surface"),
    [
        ("João é pai de Maria.", "FATHER_OF", "pai de"),
        ("Ana é a mãe de João.", "MOTHER_OF", "mãe de"),
        ("Rafael é filho de Ana.", "SON_OF", "filho de"),
        ("Clara é filha de Pedro.", "DAUGHTER_OF", "filha de"),
        ("Lucas é irmão de Marina.", "BROTHER_OF", "irmão de"),
        ("Marina é irmã de Lucas.", "SISTER_OF", "irmã de"),
        ("João é marido de Maria.", "SPOUSE_OF", "marido de"),
        ("Maria é esposa de João.", "SPOUSE_OF", "esposa de"),
        ("João é cônjuge de Maria.", "SPOUSE_OF", "cônjuge de"),
    ],
)
def test_a0_normalizes_every_approved_surface(
    text: str, relation_type: str, surface: str
) -> None:
    """Detect and normalize the approved lexical vocabulary."""

    result = extract_relations(text, "test", "A0")
    assert [(c.relation_type, c.relation_surface_text) for c in result.candidates] == [
        (relation_type, surface)
    ]


def test_unsupported_phrase_abstains() -> None:
    """Do not map a merely related word to the closest enum."""

    assert extract_relations("João falou sobre paternidade.", "test", "A0").candidates == []


@pytest.mark.parametrize(
    "text",
    [
        "João falou com o pai de Maria.",
        "Pedro conversou com a irmã de Ana.",
        "João encontrou o marido de Carla.",
        'A frase "João é pai de Maria" apareceu no documento.',
        "João é como um irmão para Maria.",
        "João se casou com Maria em 2019.",
        "Maria deu à luz João em 2001.",
    ],
)
def test_non_claim_and_event_only_text_abstains(text: str) -> None:
    """Resist incidental, quoted, metaphorical, and event-derived relations."""

    assert extract_relations(text, "test", "A0").candidates == []


@pytest.mark.parametrize(
    ("text", "field", "expected"),
    [
        ("João não é pai de Maria.", "polarity", "NEGATED"),
        ("João nunca foi pai de Maria.", "polarity", "NEGATED"),
        ("Talvez João seja pai de Maria.", "epistemic_status", "UNCERTAIN"),
        ("Acho que João é pai de Maria.", "epistemic_status", "UNCERTAIN"),
        ("João pode ser pai de Maria.", "epistemic_status", "UNCERTAIN"),
        ("Não tenho certeza se João é pai de Maria.", "epistemic_status", "UNCERTAIN"),
        ("Se João fosse pai de Maria, saberia.", "epistemic_status", "HYPOTHETICAL"),
        ("João seria pai de Maria se isso fosse verdade.", "epistemic_status", "HYPOTHETICAL"),
        ("Pedro disse que João é pai de Maria.", "reporting_mode", "REPORTED"),
        ("Maria contou que Ana é mãe de João.", "reporting_mode", "REPORTED"),
        ("Pedro afirmou que João é irmão de Carlos.", "reporting_mode", "REPORTED"),
        ("João foi marido de Maria.", "temporal_scope", "PAST"),
        ("Ana era esposa de Pedro.", "temporal_scope", "PAST"),
        ("João é marido de Maria.", "temporal_scope", "CURRENT_OR_UNSPECIFIED"),
    ],
)
def test_compositional_guards(text: str, field: str, expected: str) -> None:
    """Classify each independent linguistic safety dimension."""

    candidate = extract_relations(text, "test", "A0").candidates[0]
    assert getattr(candidate, field) == expected


def test_reporting_speaker_is_not_endpoint() -> None:
    """Keep reporting source separate from relation endpoints."""

    candidate = extract_relations(
        "Pedro disse a João que Carlos é pai de Maria.", "test", "A0"
    ).candidates[0]
    assert (candidate.endpoint_a_mention, candidate.endpoint_b_mention) == (
        "Carlos", "Maria"
    )
    assert candidate.reporting_source_mention == "Pedro"


def test_pronoun_endpoint_is_safe_abstention() -> None:
    """Preserve local pronoun text without claiming it is resolved."""

    candidate = extract_relations("Ele é pai de Maria.", "test", "A0").candidates[0]
    assert candidate.endpoint_a_mention == "Ele"
    assert candidate.endpoint_a_resolution_state == "UNRESOLVED_MENTION"
    assert candidate.persistence_eligibility == "NOT_PERSISTIBLE_PARTIAL_ENDPOINT"


def test_partial_generic_endpoint_is_safe_abstention() -> None:
    """Preserve a generic phrase but block linguistic eligibility."""

    candidate = extract_relations(
        "Minha mãe é filha de alguém que eu não conheço.", "test", "A0"
    ).candidates[0]
    assert candidate.endpoint_a_mention == "Minha mãe"
    assert candidate.endpoint_b_mention == "alguém que eu não conheço"
    assert candidate.endpoint_b_resolution_state == "UNRESOLVED_MENTION"


def test_coordination_expands_binary_candidates() -> None:
    """Represent one coordinated object list as two binary candidates."""

    candidates = extract_relations(
        "João é pai de Maria e Pedro.", "test", "A0"
    ).candidates
    assert [(item.endpoint_a_mention, item.endpoint_b_mention) for item in candidates] == [
        ("João", "Maria"), ("João", "Pedro")
    ]


def test_multiple_relations_do_not_cross_contaminate() -> None:
    """Keep endpoints independent across explicit clauses."""

    candidates = extract_relations(
        "João é pai de Maria e Pedro é irmão de Ana.", "test", "A0"
    ).candidates
    assert [
        (item.relation_type, item.endpoint_a_mention, item.endpoint_b_mention)
        for item in candidates
    ] == [
        ("FATHER_OF", "João", "Maria"),
        ("BROTHER_OF", "Pedro", "Ana"),
    ]


def test_reported_uncertain_negated_dimensions_compose() -> None:
    """Do not collapse independent safety dimensions."""

    uncertain = extract_relations(
        "Pedro disse que talvez João seja pai de Maria.", "test", "A0"
    ).candidates[0]
    negated = extract_relations(
        "Maria disse que João não é pai de Ana.", "test", "A0"
    ).candidates[0]
    assert (uncertain.epistemic_status, uncertain.reporting_mode) == (
        "UNCERTAIN", "REPORTED"
    )
    assert (negated.polarity, negated.reporting_mode) == ("NEGATED", "REPORTED")


def test_question_is_never_linguistically_eligible() -> None:
    """Treat question syntax as uncertainty."""

    candidate = extract_relations("João é pai de Maria?", "test", "A0").candidates[0]
    assert candidate.epistemic_status == "UNCERTAIN"
    assert candidate.persistence_eligibility == "NOT_PERSISTIBLE_UNCERTAIN"


def test_gliner_adapter_uses_same_downstream_pipeline() -> None:
    """Feed B/C evidence through the exact shared normalizer and guards."""

    text = "João não é pai de Maria."
    start = text.index("pai de")
    raw = {"entities": {"father relation": [{
        "text": "pai de", "start": start, "end": start + 6, "confidence": 0.8
    }]}}
    candidate = extract_relations(text, "test", "B", 0.5, raw).candidates[0]
    assert candidate.relation_type == "FATHER_OF"
    assert candidate.polarity == "NEGATED"


def test_unrecognized_gliner_span_abstains_at_normalization() -> None:
    """Reject model evidence unsupported by approved lexical text."""

    text = "João conhece Maria."
    raw = {"entities": {"person relationship expression": [{
        "text": "conhece", "start": 5, "end": 12, "confidence": 0.9
    }]}}
    assert extract_relations(text, "test", "C", 0.5, raw).candidates == []


def test_candidate_has_no_graph_identity_fields() -> None:
    """Checkpoint B stops before Person binding."""

    candidate = extract_relations("João é pai de Maria.", "test", "A0").candidates[0]
    assert all("person_id" not in name for name in type(candidate).model_fields)
