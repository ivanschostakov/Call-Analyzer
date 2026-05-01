import json
import logging
from collections import defaultdict
from datetime import datetime

from openai.types import ResponsesModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import OPENAI_API_KEY, OPENAI_MODEL
from src.app.modules.analysis.schemas import (
    PerformanceCallData,
    PerformanceChartInternalResult,
    PerformanceCriterionScore,
)
from src.app.observability import log_info, log_warning
from src.app.openai_client import build_openai_async_client
from src.database.crud import save_analysis_result_scores
from src.database.models import Analysis, AnalysisResult
from src.enums import CriterionAnswerType

logger = logging.getLogger(__name__)

_VALID_SCORES = {0, 25, 50, 75, 100}

_SCORING_PROMPT = """
You are scoring short text answers from call quality assessments.
Each answer was written by an AI analyst after reviewing a sales call.

Score each answer using ONLY these values — no other numbers:
  0   = completely absent, not attempted, irrelevant
  25  = poor — attempted but with major gaps
  50  = adequate — basic level, clear room for improvement
  75  = good — solid work, only minor issues
  100 = excellent — thorough and professional

Return a JSON object where each key is the index string ("0", "1", ...) and each value is the score.
Return ONLY the JSON object. No explanation. No markdown.

Answers to score:
""".strip()


def _deterministic_score(answer_type: CriterionAnswerType, result: AnalysisResult) -> int | None:
    if answer_type == CriterionAnswerType.PERCENTAGE:
        v = result.answer_number
        return int(v) if isinstance(v, int) and not isinstance(v, bool) else None
    if answer_type == CriterionAnswerType.BOOLEAN:
        v = result.answer_bool
        return 100 if v is True else (0 if v is False else None)
    return None


class PerformanceChartService:
    def __init__(self, openai_api_key: str | None = OPENAI_API_KEY, model_name: ResponsesModel | None = OPENAI_MODEL):
        self.__client = build_openai_async_client(openai_api_key)
        self.__model_name = model_name

    async def _ai_score_results(self, results: list[AnalysisResult]) -> dict[int, int]:
        """
        Ask the AI to score a batch of text results.
        Input: stored text answers (not the transcript).
        Output: {result.id: score} for valid responses.
        Scores are always one of {0, 25, 50, 75, 100}.
        """
        if not self.__client or not results:
            return {}

        lines = []
        for idx, result in enumerate(results):
            lines.append(f'[{idx}] Criterion: "{result.criterion_name}" | Answer: "{(result.answer_text or "").strip()}"')

        prompt = _SCORING_PROMPT + "\n\n" + "\n".join(lines)

        try:
            response = await self.__client.responses.create(
                model=self.__model_name,
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                temperature=0,
            )
            raw = response.output_text.strip()
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:])
                if raw.endswith("```"):
                    raw = raw[:-3]
            parsed = json.loads(raw)
            out: dict[int, int] = {}
            for idx_str, score in parsed.items():
                idx = int(idx_str)
                if 0 <= idx < len(results) and isinstance(score, int) and score in _VALID_SCORES:
                    out[results[idx].id] = score
            return out
        except Exception as exc:
            log_warning(logger, "performance_chart.ai_scoring.failed", extra={"error": str(exc)})
            return {}

    async def generate_chart(
        self,
        *,
        analyses: list[Analysis],
        template_name: str,
        db: AsyncSession,
    ) -> PerformanceChartInternalResult:
        log_info(logger, "performance_chart.start", template_name=template_name, analysis_count=len(analyses))

        if not analyses:
            return PerformanceChartInternalResult(calls=[])

        # Collect text results that have no stored score yet
        unscored: list[AnalysisResult] = [
            result
            for analysis in analyses
            for result in analysis.results
            if result.answer_type == CriterionAnswerType.TEXT and getattr(result, "score", None) is None
        ]

        # Score them with AI in one batched call, then persist so next time is instant
        if unscored:
            new_scores = await self._ai_score_results(unscored)
            if new_scores:
                await save_analysis_result_scores(db, new_scores)
                score_by_id = {r.id: new_scores[r.id] for r in unscored if r.id in new_scores}
                for result in unscored:
                    if result.id in score_by_id:
                        result.score = score_by_id[result.id]  # type: ignore[assignment]

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

            # Aggregate criteria scores across all calls in this day
            criterion_day_scores: dict[str, list[float]] = {}
            for analysis in day_analyses:
                for result in analysis.results:
                    score = getattr(result, "score", None)
                    if score is None:
                        score = _deterministic_score(result.answer_type, result)
                    if score is not None:
                        criterion_day_scores.setdefault(result.criterion_name, []).append(float(score))

            criteria = [
                PerformanceCriterionScore(name=name, score=round(sum(s) / len(s), 1))
                for name, s in sorted(criterion_day_scores.items())
            ]
            all_scores = [c.score for c in criteria]
            overall = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

            label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b")

            calls.append(PerformanceCallData(
                call_count=len(day_analyses),
                label=label,
                call_date=date_str,
                overall_score=overall,
                criteria_scores=criteria,
            ))

        log_info(logger, "performance_chart.success", template_name=template_name, day_count=len(calls))
        return PerformanceChartInternalResult(calls=calls)


performance_chart_service = PerformanceChartService()

__all__ = ["PerformanceChartService", "performance_chart_service"]
