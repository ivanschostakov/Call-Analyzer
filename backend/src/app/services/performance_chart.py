import logging
from collections import defaultdict
from datetime import datetime

from src.app.modules.analysis.schemas import (
    PerformanceCallData,
    PerformanceChartInternalResult,
)
from src.app.observability import log_info
from src.database.models import Analysis, AnalysisResult
from src.enums import CriterionAnswerType

logger = logging.getLogger(__name__)


def _deterministic_score(answer_type: CriterionAnswerType, result: AnalysisResult) -> int | None:
    if answer_type == CriterionAnswerType.PERCENTAGE:
        v = result.answer_number
        return int(v) if isinstance(v, int) and not isinstance(v, bool) else None
    if answer_type == CriterionAnswerType.BOOLEAN:
        v = result.answer_bool
        return 100 if v is True else (0 if v is False else None)
    return None


class PerformanceChartService:
    async def generate_chart(
        self,
        *,
        analyses: list[Analysis],
        template_name: str,
    ) -> PerformanceChartInternalResult:
        log_info(logger, "performance_chart.start", template_name=template_name, analysis_count=len(analyses))

        if not analyses:
            return PerformanceChartInternalResult(calls=[])

        def _call_dt(a: Analysis):
            t = a.transcription
            return getattr(t, "call_started_at", None) or a.created_at

        # Group analyses by calendar day
        day_groups: dict[str, list[Analysis]] = defaultdict(list)
        for analysis in analyses:
            day_groups[_call_dt(analysis).strftime("%Y-%m-%d")].append(analysis)

        calls: list[PerformanceCallData] = []
        for date_str in sorted(day_groups.keys()):
            day_analyses = day_groups[date_str]

            day_scores: list[float] = []
            for analysis in day_analyses:
                for result in analysis.results:
                    score = getattr(result, "score", None)
                    if score is None:
                        score = _deterministic_score(result.answer_type, result)
                    if score is not None:
                        day_scores.append(float(score))

            overall = round(sum(day_scores) / len(day_scores), 1) if day_scores else 0.0

            label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b")

            calls.append(PerformanceCallData(
                call_count=len(day_analyses),
                label=label,
                call_date=date_str,
                overall_score=overall,
            ))

        log_info(logger, "performance_chart.success", template_name=template_name, day_count=len(calls))
        return PerformanceChartInternalResult(calls=calls)


performance_chart_service = PerformanceChartService()

__all__ = ["PerformanceChartService", "performance_chart_service"]
