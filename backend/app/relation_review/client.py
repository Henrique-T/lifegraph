"""HTTP boundary for the frozen deterministic relation extractor."""

from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.extraction.client import (
    ExtractionServiceError,
    ExtractionServiceUnavailableError,
    MalformedExtractionResponseError,
)
from app.relations.enums import (
    EndpointMentionResolution,
    EndpointSemanticTarget,
    EpistemicStatus,
    RelationPolarity,
    RelationTemporalScope,
    RelationType,
    ReportingMode,
)
from app.relations.schemas import RelationCandidate


class WireModel(BaseModel):
    """Reject deviations from the frozen service response."""

    model_config = ConfigDict(extra="forbid")


class WireDetection(WireModel):
    text: str
    start: int
    end: int
    label: str
    confidence: float


class WireCandidate(WireModel):
    candidate_id: str
    source_reference: str
    source_text: str
    relation_type: RelationType
    relation_surface_text: str
    relation_span_start: int
    relation_span_end: int
    endpoint_a_mention: str | None
    endpoint_a_span_start: int | None
    endpoint_a_span_end: int | None
    endpoint_a_resolution_state: EndpointMentionResolution
    endpoint_a_semantic_target: EndpointSemanticTarget
    endpoint_b_mention: str | None
    endpoint_b_span_start: int | None
    endpoint_b_span_end: int | None
    endpoint_b_resolution_state: EndpointMentionResolution
    endpoint_b_semantic_target: EndpointSemanticTarget
    polarity: RelationPolarity
    epistemic_status: EpistemicStatus
    reporting_mode: ReportingMode
    reporting_source_mention: str | None
    temporal_scope: RelationTemporalScope
    warnings: list[str]
    pipeline_id: Literal["LIFEGRAPH_PERSON_RELATION_V1"]
    model_id: Literal["deterministic-structural-baseline"]
    model_revision: Literal["A0_B2+B3+B4"]
    configuration_hash: Literal["32040A53D33F30A4DDDBA0E423180AB9DC08AF17B583BB6B3A9A82BEA091FC7D"]
    detector_strategy: Literal["A0"]
    detector_label: str
    detector_confidence: float = Field(ge=0, le=1)
    persistence_eligibility: str


class WireResult(WireModel):
    source_text: str
    strategy: Literal["A0"]
    threshold: float
    detections: list[WireDetection]
    candidates: list[WireCandidate]


class RelationExtractionClient:
    """Call only the frozen relation-specific extraction endpoint."""

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url=str(settings.gliner_base_url).rstrip("/"),
            timeout=httpx.Timeout(settings.gliner_timeout_seconds),
            transport=transport,
        )

    async def extract(self, text: str, source_reference: str) -> list[RelationCandidate]:
        """Validate frozen provenance and adapt candidates without graph identities."""

        try:
            response = await self._client.post(
                "/relation-extract",
                json={"text": text, "source_reference": source_reference},
            )
        except httpx.RequestError as exc:
            raise ExtractionServiceUnavailableError("Relation extraction service is unavailable") from exc
        if response.status_code == 503:
            raise ExtractionServiceUnavailableError("Relation extraction service is unavailable")
        if response.status_code >= 400:
            raise ExtractionServiceError(
                f"Relation extraction service returned HTTP {response.status_code}"
            )
        try:
            wire = WireResult.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise MalformedExtractionResponseError("Malformed frozen relation extraction response") from exc
        return [
            RelationCandidate.model_validate(
                item.model_dump(exclude={
                    "detector_strategy", "detector_label", "detector_confidence",
                    "persistence_eligibility",
                })
            )
            for item in wire.candidates
        ]

    async def close(self) -> None:
        """Release HTTP resources."""

        await self._client.aclose()
