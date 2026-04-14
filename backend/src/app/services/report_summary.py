import logging

from dataclasses import dataclass

from openai.types import ResponsesModel

from config import LOG_ANALYZER_PAYLOADS_ENABLED, OPENAI_API_KEY, OPENAI_MODEL
from src.app.openai_client import build_openai_async_client
from src.app.modules.analysis.helpers import ReportSummaryColumnDefinition, ReportSummaryRow, serialize_report_summary_rows
from src.app.observability import log_info, log_warning, start_timer

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReportSummaryResult:
    text: str
    summarized_row_count: int
    omitted_row_count: int


class ReportSummaryService:
    SYSTEM_PROMPT = """
Ты помогаешь пользователю быстро понять отчет по звонкам.

Правила ответа:
- отвечай только в текстовом формате на русском языке;
- опирайся только на данные из отчета и вопрос пользователя;
- не выдумывай факты и не додумывай скрытые причины без опоры на отчет;
- если данных недостаточно, прямо скажи об этом;
- делай выводы по выбранным строкам и выбранным колонкам отчета;
- если в контекст попала не вся выборка, коротко отметь это в ответе.
    """.strip()

    def __init__(self, openai_api_key: str | None = OPENAI_API_KEY, model_name: ResponsesModel | None = OPENAI_MODEL):
        self.__client = build_openai_async_client(openai_api_key)
        self.__model_name = model_name

    def _get_client(self):
        if self.__client is None:
            raise RuntimeError("OpenAI is not configured. Set OPENAI_API_KEY.")
        return self.__client

    @staticmethod
    def _extract_response_text(response) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output = getattr(response, "output", []) or []
        for item in output:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if isinstance(text, str) and text.strip():
                    return text.strip()
        return ""

    @staticmethod
    def build_user_prompt(
        *,
        template_name: str,
        question: str,
        columns: list[ReportSummaryColumnDefinition],
        selected_row_count: int,
        summarized_row_count: int,
        omitted_row_count: int,
        rows_text: str,
    ) -> str:
        selected_columns = ", ".join(column.label for column in columns)
        omitted_note = (
            f"В контекст не поместилось строк: {omitted_row_count}."
            if omitted_row_count
            else "В контекст поместились все выбранные строки."
        )
        return (
            f"Отчет: {template_name}\n"
            f"Вопрос пользователя: {question.strip()}\n"
            f"Выбранные колонки: {selected_columns}\n"
            f"Выбрано строк: {selected_row_count}\n"
            f"Строк в контексте: {summarized_row_count}\n"
            f"{omitted_note}\n\n"
            f"Данные отчета:\n{rows_text}"
        ).strip()

    async def summarize_report(
        self,
        *,
        template_name: str,
        question: str,
        columns: list[ReportSummaryColumnDefinition],
        rows: list[ReportSummaryRow],
    ) -> ReportSummaryResult:
        rows_text, omitted_row_count = serialize_report_summary_rows(columns, rows)
        summarized_row_count = max(len(rows) - omitted_row_count, 0)
        timer = start_timer()
        user_prompt = self.build_user_prompt(
            template_name=template_name,
            question=question,
            columns=columns,
            selected_row_count=len(rows),
            summarized_row_count=summarized_row_count,
            omitted_row_count=omitted_row_count,
            rows_text=rows_text,
        )
        log_info(
            logger,
            "report_summary.start",
            model=self.__model_name,
            template_name=template_name,
            selected_row_count=len(rows),
            summarized_row_count=summarized_row_count,
            omitted_row_count=omitted_row_count,
            selected_column_count=len(columns),
            question_characters=len(question.strip()),
        )
        if LOG_ANALYZER_PAYLOADS_ENABLED:
            log_info(
                logger,
                "report_summary.payload",
                model=self.__model_name,
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )

        response = await self._get_client().responses.create(
            model=self.__model_name,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": self.SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
        )
        text = self._extract_response_text(response)
        if not text:
            log_warning(logger, "report_summary.empty_response", model=self.__model_name, template_name=template_name)
            raise RuntimeError("Summarizer returned an empty response.")

        log_info(
            logger,
            "report_summary.success",
            model=self.__model_name,
            template_name=template_name,
            duration_ms=timer.elapsed_ms,
            summarized_row_count=summarized_row_count,
            omitted_row_count=omitted_row_count,
            text=text if LOG_ANALYZER_PAYLOADS_ENABLED else None,
        )
        return ReportSummaryResult(
            text=text,
            summarized_row_count=summarized_row_count,
            omitted_row_count=omitted_row_count,
        )


report_summary_service = ReportSummaryService()

__all__ = ["ReportSummaryResult", "ReportSummaryService", "report_summary_service"]
