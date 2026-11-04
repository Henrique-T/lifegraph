"""Unit tests for domain-schema invariants."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.enums import Origin, VerificationStatus
from app.domain.schemas import ClaimEventCreate, RefEventCreate


def test_claim_event_defaults_preserve_declaration() -> None:
    """Verify claim event defaults preserve declaration."""
    claim = ClaimEventCreate(event_type="casamento")
    assert claim.origin is Origin.CONVERSATION
    assert claim.verification_status is VerificationStatus.DECLARED


@pytest.mark.parametrize("origin", ["USER", "REGISTRY", "unknown"])
def test_invalid_origin_is_rejected(origin: str) -> None:
    """Verify invalid origin is rejected."""
    with pytest.raises(ValidationError):
        ClaimEventCreate(event_type="casamento", origin=origin)


def test_invalid_verification_status_is_rejected() -> None:
    """Verify invalid verification status is rejected."""
    with pytest.raises(ValidationError):
        ClaimEventCreate(event_type="casamento", verification_status="VERIFIED")


def test_invalid_event_type_is_rejected() -> None:
    """Verify invalid event type is rejected."""
    with pytest.raises(ValidationError):
        ClaimEventCreate(event_type="divorcio")


def test_ref_event_requires_ref_origin() -> None:
    """Verify ref event requires ref origin."""
    with pytest.raises(ValidationError):
        RefEventCreate(
            external_ref_id="test-ref",
            event_type="casamento",
            origin="CONVERSATION",
            registration_date=datetime.now(timezone.utc),
        )


def test_year_is_an_interval_not_an_assumed_day() -> None:
    """Verify year is an interval not an assumed day."""
    claim = ClaimEventCreate(
        event_type="casamento",
        claimed_date_start="2019-01-01T00:00:00Z",
        claimed_date_end="2019-12-31T23:59:59Z",
        temporal_precision="YEAR",
    )
    assert claim.claimed_date_start.month == 1
    assert claim.claimed_date_end.month == 12


def test_unknown_precision_rejects_dates() -> None:
    """Verify unknown precision rejects dates."""
    with pytest.raises(ValidationError):
        ClaimEventCreate(
            event_type="casamento",
            claimed_date_start="2019-01-01T00:00:00Z",
            claimed_date_end="2019-12-31T23:59:59Z",
        )


def test_temporal_values_must_be_timezone_aware() -> None:
    """Verify temporal values must be timezone aware."""
    with pytest.raises(ValidationError):
        ClaimEventCreate(
            event_type="casamento",
            claimed_date_start="2019-01-01T00:00:00",
            claimed_date_end="2019-12-31T23:59:59",
            temporal_precision="YEAR",
        )
