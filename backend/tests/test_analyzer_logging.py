import logging
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from conftest import event_records
from src.analyzer import main as analyzer_main
from src.analyzer.main import CallAnalyzer
from src.analyzer.request import AnalyzerRequest
from src.analyzer.schemas.response import AnalyzerResponse
from src.database.schemas import CriterionRead
from src.enums import CriterionAnswerType


@pytest.mark.asyncio
async def test_analyzer_logs_prompts_and_raw_response(caplog) -> None:
    raw_json = '{"summary":"Call summary","employee_id":7,"criteria_evaluated":[]}'
    parsed_response = AnalyzerResponse(summary="Call summary", employee_id=7, criteria_evaluated=[])

    class FakeResponsesApi:
        async def parse(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(
                id="resp_123",
                output_text=raw_json,
                output_parsed=parsed_response,
                output=[
                    SimpleNamespace(type="file_search_call"),
                    SimpleNamespace(type="message"),
                ],
            )

    fake_responses_api = FakeResponsesApi()
    analyzer = CallAnalyzer(openai_api_key="test-key", model_name="gpt-test")
    analyzer._CallAnalyzer__client = SimpleNamespace(responses=fake_responses_api)

    criterion = CriterionRead(
        id=1,
        template_id=2,
        name="Greeting",
        description="Was the greeting good?",
        prompt="Check greeting quality",
        answer_type=CriterionAnswerType.TEXT,
        position=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    caplog.set_level(logging.INFO)
    result = await analyzer.analyze(
        AnalyzerRequest(
            call_transcription_text="Hello and welcome",
            criteria=[criterion],
            instructions="Analyze this call carefully.",
            employee_options={7: "Иван Петров"},
            vector_store_ids=["vs_123"],
        )
    )

    assert result.summary == "Call summary"
    assert fake_responses_api.kwargs["text_format"] is AnalyzerResponse

    payload_record = event_records(caplog, "analyzer.request.payload")[0]
    response_record = event_records(caplog, "analyzer.request.response")[0]
    parsed_record = event_records(caplog, "analyzer.request.parsed")[0]

    assert "Analyze this call carefully." in payload_record.event_fields["system_prompt"]
    assert "Hello and welcome" in payload_record.event_fields["user_prompt"]
    assert '"7": "Иван Петров"' in payload_record.event_fields["user_prompt"]
    assert response_record.event_fields["raw_response_text"] == raw_json
    assert parsed_record.event_fields["criteria_result_count"] == 0


@pytest.mark.asyncio
async def test_analyzer_omits_sensitive_payloads_when_disabled(caplog, monkeypatch) -> None:
    raw_json = '{"summary":"Call summary","employee_id":null,"criteria_evaluated":[]}'
    parsed_response = AnalyzerResponse(summary="Call summary", employee_id=None, criteria_evaluated=[])

    class FakeResponsesApi:
        async def parse(self, **kwargs):
            return SimpleNamespace(
                id="resp_456",
                output_text=raw_json,
                output_parsed=parsed_response,
                output=[SimpleNamespace(type="message")],
            )

    monkeypatch.setattr(analyzer_main, "LOG_ANALYZER_PAYLOADS_ENABLED", False)

    analyzer = CallAnalyzer(openai_api_key="test-key", model_name="gpt-test")
    analyzer._CallAnalyzer__client = SimpleNamespace(responses=FakeResponsesApi())

    criterion = CriterionRead(
        id=1,
        template_id=2,
        name="Greeting",
        description="Was the greeting good?",
        prompt="Check greeting quality",
        answer_type=CriterionAnswerType.TEXT,
        position=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    caplog.set_level(logging.INFO)
    await analyzer.analyze(
        AnalyzerRequest(
            call_transcription_text="Highly sensitive transcript text",
            criteria=[criterion],
            instructions="Analyze this call carefully.",
            vector_store_ids=["vs_123"],
        )
    )

    assert not event_records(caplog, "analyzer.request.payload")

    response_record = event_records(caplog, "analyzer.request.response")[0]
    parsed_record = event_records(caplog, "analyzer.request.parsed")[0]

    assert "raw_response_text" not in response_record.event_fields
    assert "summary" not in parsed_record.event_fields
    assert parsed_record.event_fields["summary_characters"] == len("Call summary")
