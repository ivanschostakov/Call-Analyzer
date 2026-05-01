from datetime import datetime
from types import SimpleNamespace

import pytest

from src.app.services.performance_chart import PerformanceChartService
from src.enums import CriterionAnswerType


@pytest.mark.asyncio
async def test_generate_chart_returns_only_day_level_overall_scores() -> None:
    service = PerformanceChartService()
    call_started_at = datetime(2026, 1, 15, 10, 30)

    analyses = [
        SimpleNamespace(
            created_at=call_started_at,
            transcription=SimpleNamespace(call_started_at=call_started_at),
            results=[
                SimpleNamespace(
                    answer_type=CriterionAnswerType.PERCENTAGE,
                    answer_number=80,
                    answer_bool=None,
                    score=None,
                ),
                SimpleNamespace(
                    answer_type=CriterionAnswerType.BOOLEAN,
                    answer_number=None,
                    answer_bool=True,
                    score=None,
                ),
                SimpleNamespace(
                    answer_type=CriterionAnswerType.TEXT,
                    answer_number=None,
                    answer_bool=None,
                    score=60,
                ),
            ],
        )
    ]

    result = await service.generate_chart(
        analyses=analyses,
        template_name="Sales QA",
    )

    assert result.model_dump() == {
        "calls": [
            {
                "call_count": 1,
                "label": "15 Jan",
                "call_date": "2026-01-15",
                "overall_score": 80.0,
            }
        ]
    }
