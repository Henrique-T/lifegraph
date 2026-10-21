"""Pure V1 persistence-eligibility evaluation for relation candidates."""

from app.relations.enums import (
    EndpointMentionResolution,
    EpistemicStatus,
    PersistenceEligibility,
    RelationPolarity,
    RelationTemporalScope,
    ReportingMode,
)
from app.relations.schemas import (
    GroundedTextCorrection,
    RelationEligibilityDecision,
    RelationPersistenceProposal,
)


def _correction_is_grounded(
    correction: GroundedTextCorrection | None,
    source_text: str,
) -> bool:
    """Return whether an optional correction is grounded in the source."""

    return correction is None or correction.is_grounded_in(source_text)


def evaluate_relation_persistence(
    proposal: RelationPersistenceProposal,
) -> RelationEligibilityDecision:
    """Return the first V1 blocker in the frozen precedence order.

    Person IDs are explicit reviewer bindings whose existence must be verified by
    the future calling service. This pure checkpoint performs no database access.
    """

    candidate = proposal.candidate
    if candidate.polarity is RelationPolarity.NEGATED:
        reason = PersistenceEligibility.NOT_PERSISTIBLE_NEGATED
    elif candidate.epistemic_status is EpistemicStatus.HYPOTHETICAL:
        reason = PersistenceEligibility.NOT_PERSISTIBLE_HYPOTHETICAL
    elif candidate.epistemic_status is EpistemicStatus.UNCERTAIN:
        reason = PersistenceEligibility.NOT_PERSISTIBLE_UNCERTAIN
    elif candidate.reporting_mode is ReportingMode.REPORTED:
        reason = PersistenceEligibility.NOT_PERSISTIBLE_REPORTED
    else:
        endpoint_a_resolved = (
            candidate.endpoint_a_resolution_state
            is EndpointMentionResolution.RESOLVED_MENTION
            or proposal.corrections.endpoint_a is not None
        )
        endpoint_b_resolved = (
            candidate.endpoint_b_resolution_state
            is EndpointMentionResolution.RESOLVED_MENTION
            or proposal.corrections.endpoint_b is not None
        )
        if not endpoint_a_resolved or not endpoint_b_resolved:
            reason = PersistenceEligibility.NOT_PERSISTIBLE_PARTIAL_ENDPOINT
        elif candidate.temporal_scope is not RelationTemporalScope.CURRENT_OR_UNSPECIFIED:
            reason = PersistenceEligibility.NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE
        elif not proposal.endpoint_a_person_id or not proposal.endpoint_b_person_id:
            reason = PersistenceEligibility.NOT_PERSISTIBLE_UNBOUND_ENDPOINT
        elif proposal.endpoint_a_person_id == proposal.endpoint_b_person_id:
            reason = PersistenceEligibility.NOT_PERSISTIBLE_SAME_PERSON_ENDPOINTS
        else:
            corrections = proposal.corrections
            grounded = all(
                _correction_is_grounded(correction, candidate.source_text)
                for correction in (
                    corrections.relation_surface,
                    corrections.endpoint_a,
                    corrections.endpoint_b,
                )
            )
            if not grounded:
                reason = PersistenceEligibility.NOT_PERSISTIBLE_UNGROUNDED_CORRECTION
            elif not proposal.reviewer_accepted:
                reason = PersistenceEligibility.NOT_PERSISTIBLE_NOT_ACCEPTED
            else:
                reason = PersistenceEligibility.PERSISTIBLE
    return RelationEligibilityDecision(
        eligible=reason is PersistenceEligibility.PERSISTIBLE,
        reason=reason,
    )
