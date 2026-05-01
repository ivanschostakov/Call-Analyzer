import json
import logging

from openai.types import ResponsesModel
from openai.types.responses import ParsedResponse

from config import LOG_ANALYZER_PAYLOADS_ENABLED, OPENAI_API_KEY, OPENAI_MODEL
from src.analyzer.schemas.response import AnalyzerResponse
from src.app.observability import log_info, log_warning, start_timer
from src.app.openai_client import build_openai_async_client
from src.analyzer.request import AnalyzerRequest
from src.database.schemas import CriterionForAnalysis
from src.enums.default_template import MAIN_INSTRUCTIONS

logger = logging.getLogger(__name__)


class CallAnalyzer:
    OUTPUT_CONTRACT_PROMPT = """
Верни строго JSON по заданной схеме.

Правила ответа:
- summary: краткое, деловое резюме звонка.
- employee_id: id сотрудника компании, который вероятнее всего участвовал в звонке со стороны компании, либо null.
- employee_id должен быть только JSON number или null, без кавычек.
- Выбирай employee_id только из словаря сотрудников, переданного в запросе.
- Если словарь сотрудников пустой или в звонке нельзя надежно определить сотрудника, верни employee_id=null.
- Определяй employee_id только для сотрудника компании, а не для клиента.
- Для выбора employee_id используй явные признаки из разговора: представление по имени, упоминание компании, ссылки на прошлые диалоги, знание внутренних процессов, приглашения в ресурсы компании.
- Если в разговоре упомянуто несколько сотрудников и нельзя надежно понять, кто именно ведет звонок, верни employee_id=null.
- criteria_evaluated: список результатов по критериям из запроса.
- Для каждого критерия верни:
  - id: id критерия
  - answer_type: только одно из "text", "percentage", "boolean"
  - answer:
    - если answer_type="text", дай короткий ответ текстом
    - если answer_type="percentage", верни целое число от 0 до 100 как JSON number, без кавычек и без символа "%"
    - если answer_type="boolean", верни true или false
- evidence: массив коротких подтверждений из разговора
- evidence должен содержать только реальные факты, реплики или смысловые фрагменты из транскрипта.
- Если надежных подтверждений нет, верни пустой массив в evidence.
- Не выдумывай факты.
- Учитывай description и prompt конкретного критерия.
- Для percentage answer должен быть числом, а не строкой.
- Никогда не оборачивай percentage answer в кавычки.
    """.strip()

    def __init__(self, openai_api_key: str | None = OPENAI_API_KEY, model_name: ResponsesModel | None = OPENAI_MODEL):
        self.openai_api_key = openai_api_key
        client = build_openai_async_client(openai_api_key)
        if client is None:
            raise RuntimeError("OpenAI is not configured. Set OPENAI_API_KEY.")
        self.__client = client
        self.__model_name = model_name

    @classmethod
    def build_system_prompt(cls, instructions: str | None) -> str:
        base_prompt = (instructions or MAIN_INSTRUCTIONS).strip()
        return f"{base_prompt}\n\n{cls.OUTPUT_CONTRACT_PROMPT}".strip()

    @staticmethod
    def build_user_prompt(call_transcription_text: str, criteria_text: str, employee_options: dict[int, str] | None = None) -> str:
        employee_options_json = json.dumps(employee_options or {}, ensure_ascii=False, sort_keys=True)
        return f"""
Транскрипт звонка:
{call_transcription_text}

Сотрудники компании (словарь id: имя):
{employee_options_json}

Сначала определи, кто со стороны компании ведет разговор. Сопоставь этого человека только с одним id из словаря сотрудников выше.
Если надежного совпадения нет, верни employee_id как null и не угадывай.

Критерии:
{criteria_text}""".strip()

    @staticmethod
    def build_criteria_text(criteria: list[CriterionForAnalysis]) -> str:
        return "\n\n".join(
            [
                (
                    f"ID: {criterion.id}\n"
                    f"Название: {criterion.name}\n"
                    f"Тип ответа: {criterion.answer_type.value}\n"
                    f"Описание: {criterion.description or '-'}\n"
                    f"Промпт: {criterion.prompt or '-'}"
                )
                for criterion in sorted(criteria, key=lambda item: item.position)
            ]
        )

    @staticmethod
    def _extract_raw_response_text(response: ParsedResponse[AnalyzerResponse]) -> str:
        output_text = response.output_text.strip()
        if output_text:
            return output_text

        if response.output_parsed is None:
            return ""

        return response.output_parsed.model_dump_json()

    @staticmethod
    def _output_item_types(response: ParsedResponse[AnalyzerResponse]) -> list[str]:
        return [item.type for item in response.output]

    async def analyze(self, request: AnalyzerRequest) -> AnalyzerResponse:
        timer = start_timer()
        criteria_text = self.build_criteria_text(request.criteria)
        system_prompt = self.build_system_prompt(request.instructions)
        user_prompt = self.build_user_prompt(request.call_transcription_text, criteria_text, request.employee_options)
        log_info(
            logger,
            "analyzer.request.start",
            model=self.__model_name,
            criteria_count=len(request.criteria),
            employee_option_count=len(request.employee_options or {}),
            transcript_characters=len(request.call_transcription_text),
            vector_store_ids=request.vector_store_ids,
            instructions_present=bool(request.instructions and request.instructions.strip()),
        )
        if LOG_ANALYZER_PAYLOADS_ENABLED:
            log_info(
                logger,
                "analyzer.request.payload",
                model=self.__model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

        input_items = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": system_prompt,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_prompt,
                    }
                ],
            },
        ]

        tools = []
        if request.vector_store_ids:
            tools.append({"type": "file_search", "vector_store_ids": request.vector_store_ids})

        response: ParsedResponse[AnalyzerResponse] = await self.__client.responses.parse(
            model=self.__model_name,
            input=input_items,
            text_format=AnalyzerResponse,
            temperature=0,
            **({"tools": tools} if tools else {}),
        )
        raw_response_text = self._extract_raw_response_text(response)
        log_info(
            logger,
            "analyzer.request.response",
            model=self.__model_name,
            response_id=getattr(response, "id", None),
            duration_ms=timer.elapsed_ms,
            raw_response_text=raw_response_text if LOG_ANALYZER_PAYLOADS_ENABLED else None,
        )
        parsed_response = response.output_parsed
        if parsed_response is None:
            output_item_types = self._output_item_types(response)
            log_warning(
                logger,
                "analyzer.request.empty_parsed_response",
                model=self.__model_name,
                response_id=getattr(response, "id", None),
                duration_ms=timer.elapsed_ms,
                output_item_types=output_item_types,
                raw_response_text=raw_response_text if LOG_ANALYZER_PAYLOADS_ENABLED else None,
            )
            raise RuntimeError(
                f"Analyzer response did not include a parsed message. Output items: {', '.join(output_item_types) or 'unknown'}."
            )
        log_info(
            logger,
            "analyzer.request.parsed",
            summary=parsed_response.summary if LOG_ANALYZER_PAYLOADS_ENABLED else None,
            summary_characters=len(parsed_response.summary),
            criteria_result_count=len(parsed_response.criteria_evaluated),
            duration_ms=timer.elapsed_ms,
        )
        return parsed_response

analyzer = CallAnalyzer()
