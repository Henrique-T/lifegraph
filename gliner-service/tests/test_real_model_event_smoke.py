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
def test_frozen_real_runtime_smoke_documents_known_natimorto_limitation() -> None:
    """Smoke the frozen runtime without treating known natimorto behavior as a coverage gap."""

    async def run() -> None:
        model = GLiNERModel()
        await model.load()
        assert model.ready, f"pinned model failed to load: {model._load_error}"

        productive_cases = (
            ("nascimento", "João nasceu em 1990."),
            ("casamento", "João se casou com Maria em 2010."),
            ("obito", "João morreu em 2020."),
        )
        for expected_type, text in productive_cases:
            result = await model.extract(text)
            assert isinstance(result, ApprovedExtractionResult)
            assert result.pipeline_id == "LIFEGRAPH_PT_CIVIL_V1"
            assert result.model_id == MODEL_ID == "fastino/gliner2.5-multi-v1"
            assert result.model_revision == MODEL_REVISION == (
                "aaecfe45db1d828c963717054ccb868e8ad1f1d5"
            )
            _assert_grounded(text, result)
            candidates = [item for item in result.candidates if item.event_type == expected_type]
            assert candidates, (
                f"missing expected {expected_type}; observed "
                f"{[item.event_type for item in result.candidates]}"
            )

        # The pinned runtime was productively exercised for natimorto, but did not
        # return the canonical type in the controlled smoke case. This assertion
        # preserves that observed limitation without changing extraction behavior.
        natimorto_text = "O bebê foi natimorto em 2021."
        natimorto = await model.extract(natimorto_text)
        assert isinstance(natimorto, ApprovedExtractionResult)
        _assert_grounded(natimorto_text, natimorto)
        assert all(item.event_type != "natimorto" for item in natimorto.candidates)

        negative_text = "João foi ao mercado em 2020."
        negative = await model.extract(negative_text)
        _assert_grounded(negative_text, negative)
        assert negative.candidates == []

    asyncio.run(run())
