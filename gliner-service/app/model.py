import asyncio
import logging
import re
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from app.schemas import (
    ApprovedCandidate,
    ApprovedExtractionResult,
    ExtractedEventCandidate,
    ExtractionResult,
    ModelSpan,
    NormalizedTimeCandidate,
)

logger = logging.getLogger(__name__)

MODEL_ID = "fastino/gliner2.5-multi-v1"
MODEL_REVISION = "aaecfe45db1d828c963717054ccb868e8ad1f1d5"

ENTITY_LABELS = {
    "birth_event": "Explicit text saying that a human being was born or gave birth",
    "marriage_event": "Explicit text saying that people married or entered a marriage",
    "death_event": "Explicit text saying that a human being died",
    "stillbirth_event": "Explicit text describing a stillbirth or a stillborn child",
    "person": "Named people or explicit human participant mentions, including kinship mentions",
    "date": "Explicit dates, months, years, or temporal expressions",
}

EVENT_LABEL_MAP = {
    "birth_event": "nascimento",
    "marriage_event": "casamento",
    "death_event": "obito",
    "stillbirth_event": "natimorto",
}


def normalize_year(expression: str | None) -> NormalizedTimeCandidate | None:
    if expression is None or re.fullmatch(r"\d{4}", expression.strip()) is None:
        return None
    year = int(expression.strip())
    if not 1 <= year <= 9999:
        return None
    return NormalizedTimeCandidate(
        start=datetime(year, 1, 1, tzinfo=timezone.utc),
        end=datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
        temporal_precision="YEAR",
    )


def _spans(raw: dict) -> list[ModelSpan]:
    spans: list[ModelSpan] = []
    for label, values in raw.get("entities", {}).items():
        if label not in ENTITY_LABELS or not isinstance(values, list):
            continue
        for value in values:
            spans.append(
                ModelSpan(
                    label=label,
                    text=value["text"],
                    start=value["start"],
                    end=value["end"],
                    score=value["confidence"],
                )
            )
    return sorted(spans, key=lambda item: (item.start, item.end, item.label))


def map_raw_output(text: str, raw: dict, latency_ms: float) -> ExtractionResult:
    spans = _spans(raw)
    people = [item for item in spans if item.label == "person"]
    dates = [item for item in spans if item.label == "date"]
    warnings = ["UNCERTAINTY_DETECTION_UNSUPPORTED"]
    if len(dates) > 1:
        warnings.append("MULTIPLE_TEMPORAL_EXPRESSIONS_NOT_ASSOCIATED")
    temporal_expression = dates[0].text if len(dates) == 1 else None

    events = []
    for span in spans:
        event_type = EVENT_LABEL_MAP.get(span.label)
        if event_type is None:
            continue
        events.append(
            ExtractedEventCandidate(
                candidate_id=str(uuid4()),
                event_type=event_type,
                raw_event_text=span.text,
                person_mentions=people,
                temporal_expression=temporal_expression,
                normalized_time_candidate=normalize_year(temporal_expression),
                confidence=span.score,
                raw_model_evidence=span,
            )
        )
    return ExtractionResult(
        extraction_id=str(uuid4()),
        source_text=text,
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        extracted_events=events,
        raw_spans=spans,
        warnings=warnings,
        latency_ms=latency_ms,
    )


class GLiNERModel:
    def __init__(self) -> None:
        self._model = None
        self._load_error: str | None = None
        self._lock = asyncio.Lock()
        self.load_time_seconds: float | None = None

    @property
    def ready(self) -> bool:
        return self._model is not None

    @property
    def load_failed(self) -> bool:
        return self._load_error is not None

    async def load(self) -> None:
        started = perf_counter()
        try:
            from gliner2 import AutoExtractor

            self._model = await asyncio.to_thread(
                AutoExtractor.from_pretrained,
                MODEL_ID,
                revision=MODEL_REVISION,
                map_location="cpu",
            )
            self.load_time_seconds = perf_counter() - started
            logger.info(
                "GLiNER model loaded model_id=%s seconds=%.3f",
                MODEL_ID,
                self.load_time_seconds,
            )
        except Exception as exc:
            self._load_error = type(exc).__name__
            logger.exception("GLiNER model failed to load model_id=%s", MODEL_ID)

    async def extract(self, text: str) -> ApprovedExtractionResult:
        if self._model is None:
            raise RuntimeError("model unavailable")
        # Local import avoids the model/calibration module cycle. The approved
        # path is immutable and callers cannot supply a strategy or schema.
        from app.subject_association import associate

        raw = await associate(self, "S1C_CONSERVATIVE_GUARDS", text)
        candidates = [
            ApprovedCandidate(
                event_type=item["event_type"],
                trigger_text=item["trigger_text"],
                trigger_start=item["trigger_start"],
                trigger_end=item["trigger_end"],
                subject_text=item["subject_text"],
                subject_resolution=item["subject_resolution"],
                subject_reason=item["subject_reason"],
                participant_texts=item["participant_texts"],
                date_expression=item["date_expression"],
                normalized_time_candidate=normalize_year(item["date_expression"]),
                warnings=item["warnings"],
            )
            for item in raw["associated_events"]
        ]
        latency_ms = raw["stage1_latency_ms"] + raw["stage2_latency_ms"]
        result = ApprovedExtractionResult(
            source_text=text,
            model_id=MODEL_ID,
            model_revision=MODEL_REVISION,
            pipeline_id="LIFEGRAPH_PT_CIVIL_V1",
            candidates=candidates,
            warnings=["UNCERTAINTY_DETECTION_UNSUPPORTED"],
            latency_ms=max(0, latency_ms),
        )
        logger.info(
            "Extraction complete extraction_id=%s model_id=%s text_length=%d candidates=%d latency_ms=%.1f",
            "backend-assigned",
            MODEL_ID,
            len(text),
            len(result.candidates),
            latency_ms,
        )
        return result
