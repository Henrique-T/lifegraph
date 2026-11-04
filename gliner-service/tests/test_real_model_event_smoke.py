"""Opt-in smoke checks for the frozen production GLiNER event runtime.

These deliberately simple synthetic narratives are a runtime capability check,
not an evaluation corpus and not a source of precision/recall metrics.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from app.model import GLiNERModel, MODEL_ID, MODEL_REVISION
from app.schemas import ApprovedExtractionResult


RUN_REAL_SMOKE = os.getenv("RUN_REAL_GLINER_SMOKE") == "1"


def _assert_grounded(text: str, result: ApprovedExtractionResult) -> None:
    for candidate in result.candidates:
        assert 0 <= candidate.trigger_start < candidate.trigger_end <= len(text)
        assert text[candidate.trigger_start:candidate.trigger_end] == candidate.trigger_text


@pytest.mark.skipif(
    not RUN_REAL_SMOKE,
    reason="set RUN_REAL_GLINER_SMOKE=1 to load the pinned real model runtime",
)
def test_frozen_real_runtime_recognizes_all_supported_event_types() -> None:
    """Smoke the real frozen production path for the four supported types."""

    async def run() -> None:
        model = GLiNERModel()
        await model.load()
        assert model.ready, f"pinned model failed to load: {model._load_error}"

        cases = (
            ("nascimento", "João nasceu em 1990."),
            ("casamento", "João se casou com Maria em 2010."),
            ("obito", "João morreu em 2020."),
            ("natimorto", "O bebê foi natimorto em 2021."),
        )
        missing: list[tuple[str, list[str]]] = []
        for expected_type, text in cases:
            result = await model.extract(text)
            assert isinstance(result, ApprovedExtractionResult)
            assert result.pipeline_id == "LIFEGRAPH_PT_CIVIL_V1"
            assert result.model_id == MODEL_ID == "fastino/gliner2.5-multi-v1"
            assert result.model_revision == MODEL_REVISION == (
                "aaecfe45db1d828c963717054ccb868e8ad1f1d5"
            )
            _assert_grounded(text, result)
            candidates = [item for item in result.candidates if item.event_type == expected_type]
            if not candidates:
                missing.append((expected_type, [item.event_type for item in result.candidates]))

        negative_text = "João foi ao mercado em 2020."
        negative = await model.extract(negative_text)
        _assert_grounded(negative_text, negative)
        assert negative.candidates == []
        assert missing == [], f"missing expected event types (expected, observed): {missing}"

    asyncio.run(run())
