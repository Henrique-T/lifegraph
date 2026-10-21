"""Unit tests for the isolated V1 person-relation schema checkpoint."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.enums import Origin, VerificationStatus
from app.relations.canonical import canonical_pair_key, canonical_relation_family
from app.relations.eligibility import evaluate_relation_persistence
from app.relations.enums import (
    CanonicalRelationFamily,
    EndpointMentionResolution,
    EpistemicStatus,
    PersistenceEligibility,
    RelationPolarity,
    RelationTemporalScope,
    RelationType,
    ReportingMode,
)
from app.relations.schemas import (
    GroundedTextCorrection,
    RelationCandidate,
    RelationCandidateCorrections,
    RelationClaim,
    RelationPersistenceProposal,
)


def candidate(**changes: object) -> RelationCandidate:
    """Build a valid direct positive relation candidate."""

    values: dict[str, object] = {
        "candidate_id": "candidate-1",
        "source_reference": "review-1",
        "source_text": "João é pai de Maria.",
        "relation_type": RelationType.FATHER_OF,
        "relation_surface_text": "pai de",
        "relation_span_start": 7,
        "relation_span_end": 13,
        "endpoint_a_mention": "João",
        "endpoint_a_span_start": 0,
        "endpoint_a_span_end": 4,
        "endpoint_a_resolution_state": EndpointMentionResolution.RESOLVED_MENTION,
        "endpoint_b_mention": "Maria",
        "endpoint_b_span_start": 14,
        "endpoint_b_span_end": 19,
        "endpoint_b_resolution_state": EndpointMentionResolution.RESOLVED_MENTION,
        "polarity": RelationPolarity.POSITIVE,
        "epistemic_status": EpistemicStatus.ASSERTED,
        "reporting_mode": ReportingMode.DIRECT,
        "reporting_source_mention": None,
        "temporal_scope": RelationTemporalScope.CURRENT_OR_UNSPECIFIED,
        "warnings": [],
        "pipeline_id": "RELATION_V1_FUTURE",
        "model_id": "fixture",
        "model_revision": "fixture-revision",
        "configuration_hash": "fixture-config",
    }
    values.update(changes)
    return RelationCandidate.model_validate(values)


def proposal(
    relation_candidate: RelationCandidate | None = None,
    **changes: object,
) -> RelationPersistenceProposal:
    """Build an accepted proposal with two explicit reviewer bindings."""

    values: dict[str, object] = {
        "candidate": relation_candidate or candidate(),
        "endpoint_a_person_id": "person-joao",
        "endpoint_b_person_id": "person-maria",
        "reviewer_accepted": True,
    }
    values.update(changes)
    return RelationPersistenceProposal.model_validate(values)


def claim(**changes: object) -> RelationClaim:
    """Build one valid future relation-claim representation."""

    relation_type = changes.get("relation_type", RelationType.FATHER_OF)
    endpoint_a = changes.get("endpoint_a_person_id", "person-joao")
    endpoint_b = changes.get("endpoint_b_person_id", "person-maria")
    assert isinstance(relation_type, RelationType)
    assert isinstance(endpoint_a, str)
    assert isinstance(endpoint_b, str)
    values: dict[str, object] = {
        "relation_claim_id": "claim-1",
        "relation_type": relation_type,
        "endpoint_a_person_id": endpoint_a,
        "endpoint_b_person_id": endpoint_b,
        "conversation_turn_id": "turn-1",
        "original_relation_surface": "pai de",
        "original_endpoint_a_mention": "João",
        "original_endpoint_b_mention": "Maria",
        "accepted_relation_surface": "pai de",
        "accepted_endpoint_a_mention": "João",
        "accepted_endpoint_b_mention": "Maria",
        "reviewer_correction_applied": False,
        "reviewer_corrections_json": None,
        "extraction_id": "extraction-1",
        "candidate_id": "candidate-1",
        "pipeline_id": "RELATION_V1_FUTURE",
        "model_id": "fixture",
        "model_revision": "fixture-revision",
        "configuration_hash": "fixture-config",
        "acceptance_payload_hash": "payload-hash",
        "canonical_relation_family": canonical_relation_family(relation_type),
        "canonical_pair_key": canonical_pair_key(relation_type, endpoint_a, endpoint_b),
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    values.update(changes)
    return RelationClaim.model_validate(values)


@pytest.mark.parametrize(
    ("enum_type", "expected"),
    [
        (RelationType, {"FATHER_OF", "MOTHER_OF", "SON_OF", "DAUGHTER_OF", "BROTHER_OF", "SISTER_OF", "SPOUSE_OF"}),
        (RelationPolarity, {"POSITIVE", "NEGATED"}),
        (EpistemicStatus, {"ASSERTED", "UNCERTAIN", "HYPOTHETICAL"}),
        (ReportingMode, {"DIRECT", "REPORTED"}),
        (RelationTemporalScope, {"CURRENT_OR_UNSPECIFIED", "PAST", "UNRESOLVED"}),
        (EndpointMentionResolution, {"RESOLVED_MENTION", "UNRESOLVED_MENTION"}),
    ],
)
def test_approved_enum_domains(enum_type: type, expected: set[str]) -> None:
    """Freeze every approved closed vocabulary."""

    assert {item.value for item in enum_type} == expected


def test_direct_positive_current_candidate_is_persistible() -> None:
    """Allow only the complete, accepted, explicitly bound happy path."""

    decision = evaluate_relation_persistence(proposal())
    assert decision.eligible is True
    assert decision.reason is PersistenceEligibility.PERSISTIBLE


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"polarity": RelationPolarity.NEGATED}, PersistenceEligibility.NOT_PERSISTIBLE_NEGATED),
        ({"epistemic_status": EpistemicStatus.UNCERTAIN}, PersistenceEligibility.NOT_PERSISTIBLE_UNCERTAIN),
        ({"epistemic_status": EpistemicStatus.HYPOTHETICAL}, PersistenceEligibility.NOT_PERSISTIBLE_HYPOTHETICAL),
        ({"reporting_mode": ReportingMode.REPORTED}, PersistenceEligibility.NOT_PERSISTIBLE_REPORTED),
        ({"temporal_scope": RelationTemporalScope.PAST}, PersistenceEligibility.NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE),
        ({"temporal_scope": RelationTemporalScope.UNRESOLVED}, PersistenceEligibility.NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE),
    ],
)
def test_compositional_safety_blockers(
    changes: dict[str, object],
    reason: PersistenceEligibility,
) -> None:
    """Block every non-asserted or unsupported semantic dimension."""

    decision = evaluate_relation_persistence(proposal(candidate(**changes)))
    assert decision.eligible is False
    assert decision.reason is reason


def test_partial_endpoint_is_valid_for_review_but_not_persistence() -> None:
    """Represent a partial candidate without creating an Unknown identity."""

    partial = candidate(
        endpoint_b_mention=None,
        endpoint_b_span_start=None,
        endpoint_b_span_end=None,
        endpoint_b_resolution_state=EndpointMentionResolution.UNRESOLVED_MENTION,
    )
    decision = evaluate_relation_persistence(proposal(partial))
    assert partial.endpoint_b_mention is None
    assert decision.reason is PersistenceEligibility.NOT_PERSISTIBLE_PARTIAL_ENDPOINT


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"endpoint_b_person_id": None}, PersistenceEligibility.NOT_PERSISTIBLE_UNBOUND_ENDPOINT),
        ({"endpoint_b_person_id": "person-joao"}, PersistenceEligibility.NOT_PERSISTIBLE_SAME_PERSON_ENDPOINTS),
        ({"reviewer_accepted": False}, PersistenceEligibility.NOT_PERSISTIBLE_NOT_ACCEPTED),
    ],
)
def test_binding_and_acceptance_gates(
    changes: dict[str, object],
    reason: PersistenceEligibility,
) -> None:
    """Require two distinct explicit bindings and explicit acceptance."""

    decision = evaluate_relation_persistence(proposal(**changes))
    assert decision.eligible is False
    assert decision.reason is reason


def test_valid_correction_is_grounded_and_preserves_original() -> None:
    """Keep extracted provenance while accepting an exact source substring."""

    original = candidate()
    corrections = RelationCandidateCorrections(
        endpoint_a=GroundedTextCorrection(text="João", start=0, end=4),
        relation_surface=GroundedTextCorrection(text="pai de", start=7, end=13),
    )
    decision = evaluate_relation_persistence(
        proposal(original, corrections=corrections)
    )
    assert decision.eligible is True
    assert original.endpoint_a_mention == "João"
    assert original.relation_surface_text == "pai de"


@pytest.mark.parametrize(
    "correction",
    [
        GroundedTextCorrection(text="genitor de", start=7, end=13),
        GroundedTextCorrection(text="Maria", start=14, end=99),
    ],
)
def test_ungrounded_correction_is_rejected(
    correction: GroundedTextCorrection,
) -> None:
    """Reject invented text and out-of-range offsets deterministically."""

    decision = evaluate_relation_persistence(
        proposal(
            corrections=RelationCandidateCorrections(relation_surface=correction)
        )
    )
    assert decision.eligible is False
    assert decision.reason is PersistenceEligibility.NOT_PERSISTIBLE_UNGROUNDED_CORRECTION


def test_primary_blocking_reason_has_stable_precedence() -> None:
    """Return the highest-priority blocker when several apply."""

    blocked = candidate(
        endpoint_b_mention=None,
        endpoint_b_span_start=None,
        endpoint_b_span_end=None,
        endpoint_b_resolution_state=EndpointMentionResolution.UNRESOLVED_MENTION,
        polarity=RelationPolarity.NEGATED,
        epistemic_status=EpistemicStatus.UNCERTAIN,
        reporting_mode=ReportingMode.REPORTED,
        temporal_scope=RelationTemporalScope.PAST,
    )
    decision = evaluate_relation_persistence(
        proposal(
            blocked,
            endpoint_b_person_id=None,
            reviewer_accepted=False,
            corrections=RelationCandidateCorrections(
                relation_surface=GroundedTextCorrection(
                    text="invented", start=7, end=13
                )
            ),
        )
    )
    assert decision.reason is PersistenceEligibility.NOT_PERSISTIBLE_NEGATED


def test_candidate_rejects_graph_identity_and_unknown_fields() -> None:
    """Keep linguistic mentions separate from graph Person identities."""

    values = candidate().model_dump()
    values["endpoint_a_person_id"] = "person-joao"
    with pytest.raises(ValidationError):
        RelationCandidate.model_validate(values)
    assert "unknown" not in {field.casefold() for field in RelationCandidate.model_fields}


@pytest.mark.parametrize(
    ("relation_type", "family"),
    [
        (RelationType.FATHER_OF, CanonicalRelationFamily.PARENT_CHILD),
        (RelationType.MOTHER_OF, CanonicalRelationFamily.PARENT_CHILD),
        (RelationType.SON_OF, CanonicalRelationFamily.PARENT_CHILD),
        (RelationType.DAUGHTER_OF, CanonicalRelationFamily.PARENT_CHILD),
        (RelationType.BROTHER_OF, CanonicalRelationFamily.SIBLING),
        (RelationType.SISTER_OF, CanonicalRelationFamily.SIBLING),
        (RelationType.SPOUSE_OF, CanonicalRelationFamily.SPOUSE),
    ],
)
def test_structural_families(
    relation_type: RelationType,
    family: CanonicalRelationFamily,
) -> None:
    """Group structurally without changing the declared relation type."""

    assert canonical_relation_family(relation_type) is family


def test_sibling_spouse_and_parent_child_pair_canonicalization() -> None:
    """Canonicalize symmetric pairs and orient parent-child pairs."""

    assert canonical_pair_key(RelationType.BROTHER_OF, "joao", "maria") == canonical_pair_key(
        RelationType.SISTER_OF, "maria", "joao"
    )
    assert canonical_pair_key(RelationType.SPOUSE_OF, "joao", "maria") == canonical_pair_key(
        RelationType.SPOUSE_OF, "maria", "joao"
    )
    assert canonical_pair_key(RelationType.FATHER_OF, "parent", "child") == canonical_pair_key(
        RelationType.SON_OF, "child", "parent"
    )


def test_independent_claims_with_same_pair_remain_representable() -> None:
    """Ensure canonical metadata does not collapse conversational provenance."""

    first = claim()
    second = claim(relation_claim_id="claim-2", conversation_turn_id="turn-2")
    assert first.relation_claim_id != second.relation_claim_id
    assert first.conversation_turn_id != second.conversation_turn_id
    assert first.canonical_pair_key == second.canonical_pair_key


def test_declared_relation_type_is_preserved_without_inverse_generation() -> None:
    """Keep each supplied declaration unchanged and generate no reverse claim."""

    brother = claim(
        relation_type=RelationType.BROTHER_OF,
        canonical_relation_family=CanonicalRelationFamily.SIBLING,
        canonical_pair_key=canonical_pair_key(
            RelationType.BROTHER_OF, "person-joao", "person-maria"
        ),
    )
    assert brother.relation_type is RelationType.BROTHER_OF
    assert isinstance(brother, RelationClaim)


def test_relation_claim_defaults_and_constraints() -> None:
    """Restrict the future claim representation to conversational declarations."""

    relation_claim = claim()
    assert relation_claim.origin is Origin.CONVERSATION
    assert relation_claim.verification_status is VerificationStatus.DECLARED
    with pytest.raises(ValidationError):
        claim(origin=Origin.REF)
    with pytest.raises(ValidationError):
        claim(verification_status=VerificationStatus.CONFIRMED)
    with pytest.raises(ValidationError):
        claim(endpoint_b_person_id="person-joao")


def test_checkpoint_has_no_event_derived_relation_shape() -> None:
    """Exclude event semantics from the isolated relation schema layer."""

    forbidden = {"event_type", "date_expression", "participants", "ref_event_id"}
    assert forbidden.isdisjoint(RelationCandidate.model_fields)
    assert forbidden.isdisjoint(RelationClaim.model_fields)
    with pytest.raises(ValidationError):
        RelationCandidate.model_validate({**candidate().model_dump(), "event_type": "casamento"})
