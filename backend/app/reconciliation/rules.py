"""Pure deterministic rules for comparing claims with REF events."""

from app.domain.enums import TemporalPrecision, VerificationStatus
from app.domain.schemas import ClaimEventRead, RefEventRead
from app.reconciliation.schemas import ReasonCode, ReconciliationDecision


def _claim_has_interval(claim: ClaimEventRead) -> bool:
    """Return whether a claim has a usable temporal interval."""
    return (
        claim.temporal_precision is not TemporalPrecision.UNKNOWN
        and claim.claimed_date_start is not None
        and claim.claimed_date_end is not None
    )


def _inside_claim_interval(claim: ClaimEventRead, event: RefEventRead) -> bool:
    """Return whether a dated REF event falls within a claim interval."""
    assert claim.claimed_date_start is not None
    assert claim.claimed_date_end is not None
    assert event.event_date is not None
    return claim.claimed_date_start <= event.event_date <= claim.claimed_date_end


def reconcile_candidates(
    claim: ClaimEventRead, candidates: list[RefEventRead]
) -> ReconciliationDecision:
    """Reconcile one claim against same-person candidate REF events."""
    # The repository supplies same-person candidates; this second filter makes
    # the same-event-type invariant explicit at the rule boundary too.
    candidates = [item for item in candidates if item.event_type == claim.event_type]
    candidate_ids = [item.ref_event_id for item in candidates]
    if not candidates:
        return ReconciliationDecision(
            status=VerificationStatus.UNVERIFIED,
            candidate_ref_event_ids=[],
            reason_codes=[ReasonCode.NO_MATCHING_REF_EVENT_TYPE],
        )

    common = [ReasonCode.EVENT_TYPE_MATCH]
    if not _claim_has_interval(claim):
        return ReconciliationDecision(
            status=VerificationStatus.UNVERIFIED,
            candidate_ref_event_ids=candidate_ids,
            reason_codes=common + [ReasonCode.INSUFFICIENT_TEMPORAL_EVIDENCE],
        )

    known = [item for item in candidates if item.event_date is not None]
    compatible = [item for item in known if _inside_claim_interval(claim, item)]

    if len(candidates) == 1:
        candidate = candidates[0]
        if candidate.event_date is None:
            return ReconciliationDecision(
                status=VerificationStatus.UNVERIFIED,
                candidate_ref_event_ids=candidate_ids,
                reason_codes=common + [ReasonCode.INSUFFICIENT_TEMPORAL_EVIDENCE],
            )
        if compatible:
            return ReconciliationDecision(
                status=VerificationStatus.CONFIRMED,
                matched_ref_event_id=candidate.ref_event_id,
                candidate_ref_event_ids=candidate_ids,
                reason_codes=common
                + [ReasonCode.EVENT_DATE_WITHIN_CLAIM_INTERVAL],
            )
        return ReconciliationDecision(
            status=VerificationStatus.DIVERGENT,
            candidate_ref_event_ids=candidate_ids,
            reason_codes=common + [ReasonCode.EVENT_DATE_OUTSIDE_CLAIM_INTERVAL],
            contradictory_ref_event_ids=[candidate.ref_event_id],
        )

    if len(compatible) == 1:
        selected = compatible[0]
        return ReconciliationDecision(
            status=VerificationStatus.CONFIRMED,
            matched_ref_event_id=selected.ref_event_id,
            candidate_ref_event_ids=candidate_ids,
            reason_codes=common
            + [
                ReasonCode.EVENT_DATE_WITHIN_CLAIM_INTERVAL,
                ReasonCode.UNIQUE_TEMPORALLY_COMPATIBLE_CANDIDATE,
            ],
        )
    if len(compatible) > 1:
        return ReconciliationDecision(
            status=VerificationStatus.UNVERIFIED,
            candidate_ref_event_ids=candidate_ids,
            reason_codes=common
            + [ReasonCode.AMBIGUOUS_MULTIPLE_REF_CANDIDATES],
        )
    if len(known) != len(candidates):
        return ReconciliationDecision(
            status=VerificationStatus.UNVERIFIED,
            candidate_ref_event_ids=candidate_ids,
            reason_codes=common + [ReasonCode.INSUFFICIENT_TEMPORAL_EVIDENCE],
        )
    return ReconciliationDecision(
        status=VerificationStatus.DIVERGENT,
        candidate_ref_event_ids=candidate_ids,
        reason_codes=common + [ReasonCode.NO_TEMPORALLY_COMPATIBLE_REF_EVENT],
    )
