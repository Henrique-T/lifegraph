"""Unit tests for deterministic reconciliation rules."""

from datetime import datetime, timezone

from app.domain.schemas import ClaimEventRead, RefEventRead
from app.reconciliation.rules import reconcile_candidates
from app.reconciliation.schemas import ReasonCode

CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def claim(
    *,
    event_type: str = "casamento",
    start: str | None = "2019-01-01T00:00:00Z",
    end: str | None = "2019-12-31T23:59:59Z",
    precision: str = "YEAR",
) -> ClaimEventRead:
    """Create a claim fixture for the test."""
    return ClaimEventRead(
        claim_event_id="claim",
        event_type=event_type,
        origin="CONVERSATION",
        verification_status="DECLARED",
        claimed_date_start=start,
        claimed_date_end=end,
        temporal_precision=precision,
        created_at=CREATED,
    )


def ref(
    ref_id: str,
    date: str | None,
    *,
    event_type: str = "casamento",
) -> RefEventRead:
    """Create a ref fixture for the test."""
    return RefEventRead(
        ref_event_id=ref_id,
        external_ref_id=f"external-{ref_id}",
        event_type=event_type,
        origin="REF",
        event_date=date,
        registration_date=CREATED,
        created_at=CREATED,
    )


def test_exact_day_match_is_confirmed() -> None:
    """Verify exact day match is confirmed."""
    decision = reconcile_candidates(
        claim(
            start="2019-06-15T00:00:00Z",
            end="2019-06-15T23:59:59Z",
            precision="DAY",
        ),
        [ref("one", "2019-06-15T12:00:00Z")],
    )
    assert decision.status.value == "CONFIRMED"
    assert decision.matched_ref_event_id == "one"


def test_year_interval_match_is_confirmed() -> None:
    """Verify year interval match is confirmed."""
    decision = reconcile_candidates(claim(), [ref("one", "2019-06-15T00:00:00Z")])
    assert decision.status.value == "CONFIRMED"
    assert ReasonCode.EVENT_DATE_WITHIN_CLAIM_INTERVAL in decision.reason_codes


def test_date_outside_interval_is_divergent_with_specific_event() -> None:
    """Verify date outside interval is divergent with specific event."""
    decision = reconcile_candidates(claim(), [ref("one", "2021-03-01T00:00:00Z")])
    assert decision.status.value == "DIVERGENT"
    assert decision.contradictory_ref_event_ids == ["one"]


def test_no_same_type_candidate_is_unverified() -> None:
    """Verify no same type candidate is unverified."""
    decision = reconcile_candidates(claim(), [])
    assert decision.status.value == "UNVERIFIED"
    assert decision.reason_codes == [ReasonCode.NO_MATCHING_REF_EVENT_TYPE]


def test_claim_without_date_is_unverified() -> None:
    """Verify claim without date is unverified."""
    decision = reconcile_candidates(
        claim(start=None, end=None, precision="UNKNOWN"),
        [ref("one", "2019-06-15T00:00:00Z")],
    )
    assert decision.status.value == "UNVERIFIED"
    assert ReasonCode.INSUFFICIENT_TEMPORAL_EVIDENCE in decision.reason_codes


def test_ref_without_event_date_is_unverified() -> None:
    """Verify ref without event date is unverified."""
    decision = reconcile_candidates(claim(), [ref("one", None)])
    assert decision.status.value == "UNVERIFIED"


def test_multiple_candidates_with_one_match_confirms_unique_candidate() -> None:
    """Verify multiple candidates with one match confirms unique candidate."""
    decision = reconcile_candidates(
        claim(),
        [ref("outside", "2018-01-01T00:00:00Z"), ref("inside", "2019-07-01T00:00:00Z")],
    )
    assert decision.status.value == "CONFIRMED"
    assert decision.matched_ref_event_id == "inside"
    assert ReasonCode.UNIQUE_TEMPORALLY_COMPATIBLE_CANDIDATE in decision.reason_codes


def test_multiple_compatible_candidates_are_ambiguous() -> None:
    """Verify multiple compatible candidates are ambiguous."""
    decision = reconcile_candidates(
        claim(),
        [ref("one", "2019-01-01T00:00:00Z"), ref("two", "2019-12-01T00:00:00Z")],
    )
    assert decision.status.value == "UNVERIFIED"
    assert ReasonCode.AMBIGUOUS_MULTIPLE_REF_CANDIDATES in decision.reason_codes


def test_multiple_known_dates_with_zero_matches_are_divergent_collectively() -> None:
    """Verify multiple known dates with zero matches are divergent collectively."""
    decision = reconcile_candidates(
        claim(),
        [ref("one", "2017-01-01T00:00:00Z"), ref("two", "2021-01-01T00:00:00Z")],
    )
    assert decision.status.value == "DIVERGENT"
    assert decision.contradictory_ref_event_ids == []
    assert ReasonCode.NO_TEMPORALLY_COMPATIBLE_REF_EVENT in decision.reason_codes


def test_unknown_date_prevents_collective_divergence() -> None:
    """Verify unknown date prevents collective divergence."""
    decision = reconcile_candidates(
        claim(), [ref("outside", "2021-01-01T00:00:00Z"), ref("unknown", None)]
    )
    assert decision.status.value == "UNVERIFIED"


def test_event_type_mismatch_is_not_a_candidate() -> None:
    """Verify event type mismatch is not a candidate."""
    decision = reconcile_candidates(
        claim(event_type="casamento"),
        [ref("birth", "2019-06-15T00:00:00Z", event_type="nascimento")],
    )
    assert decision.status.value == "UNVERIFIED"
    assert decision.candidate_ref_event_ids == []
