import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import event_records
from src.transcriber.models import Segment, SttResult


@asynccontextmanager
async def fake_session():
    yield object()


@pytest.mark.asyncio
async def test_transcription_job_success_logs_completion(caplog, monkeypatch) -> None:
    from src.app.services import transcription_jobs as jobs

    async def fake_convert_and_transcribe(transcription_id):
        return SttResult(text="hello from transcript", language="en", segments=[Segment(start=0.0, end=1.0, text="hello")])

    async def fake_get_transcription_by_id(db, transcription_id):
        return SimpleNamespace(
            id=transcription_id,
            status="processing",
            company_id=1,
            uploaded_by_user_id=2,
        )

    async def fake_update_transcription(db, transcription, payload):
        transcription.status = payload.status.value
        transcription.language = payload.language
        transcription.text = payload.text
        transcription.segments = payload.segments
        return transcription

    async def fake_heartbeat(transcription_id):
        await asyncio.sleep(3600)

    monkeypatch.setattr(jobs, "get_session", fake_session)
    monkeypatch.setattr(jobs, "_convert_and_transcribe", fake_convert_and_transcribe)
    monkeypatch.setattr(jobs, "get_transcription_by_id", fake_get_transcription_by_id)
    monkeypatch.setattr(jobs, "update_transcription", fake_update_transcription)
    monkeypatch.setattr(jobs, "_heartbeat_processing_transcription", fake_heartbeat)

    caplog.set_level(logging.INFO)
    await jobs._process_claimed_transcription(123)

    completed_record = event_records(caplog, "transcription.job.completed")[0]

    assert completed_record.event_fields["transcription_id"] == 123
    assert completed_record.event_fields["transcript_text"] == "hello from transcript"
    assert not event_records(caplog, "transcription.job.finish")


@pytest.mark.asyncio
async def test_requeue_logs_recovered_jobs(caplog, monkeypatch) -> None:
    from src.app.services import transcription_jobs as jobs

    async def fake_requeue_processing_transcriptions(db, older_than):
        return 2

    monkeypatch.setattr(jobs, "get_session", fake_session)
    monkeypatch.setattr(jobs, "requeue_processing_transcriptions", fake_requeue_processing_transcriptions)

    caplog.set_level(logging.INFO)
    recovered = await jobs.requeue_stuck_transcription_jobs(stale_after_seconds=10)

    assert recovered == 2
    finish_record = event_records(caplog, "transcription.jobs.requeue.finish")[0]
    assert finish_record.event_fields["recovered"] == 2


@pytest.mark.asyncio
async def test_requeue_without_recovered_jobs_stays_quiet_at_info(caplog, monkeypatch) -> None:
    from src.app.services import transcription_jobs as jobs

    async def fake_requeue_processing_transcriptions(db, older_than):
        return 0

    monkeypatch.setattr(jobs, "get_session", fake_session)
    monkeypatch.setattr(jobs, "requeue_processing_transcriptions", fake_requeue_processing_transcriptions)

    caplog.set_level(logging.INFO)
    recovered = await jobs.requeue_stuck_transcription_jobs(stale_after_seconds=10)

    assert recovered == 0
    assert not event_records(caplog, "transcription.jobs.requeue.finish")


@pytest.mark.asyncio
async def test_convert_and_transcribe_passes_company_hint_prompt(monkeypatch, tmp_path) -> None:
    from src.app.services import transcription_jobs as jobs

    wav_path = tmp_path / "call.wav"
    wav_path.write_bytes(b"wav-data")

    class FakeTranscriber:
        async def transcribe(self, file_path, prompt=None):
            assert file_path == wav_path
            assert prompt == "company glossary"
            return SttResult(text="hinted transcript", language="ru", segments=[])

    async def fake_get_transcription_by_id(db, transcription_id):
        return SimpleNamespace(
            id=transcription_id,
            company_id=77,
            source_path=str(wav_path),
            file_path=str(wav_path),
        )

    async def fake_get_company_by_id(db, company_id):
        assert company_id == 77
        return SimpleNamespace(id=company_id, transcription_hint_prompt="company glossary")

    monkeypatch.setattr(jobs, "get_session", fake_session)
    monkeypatch.setattr(jobs, "get_transcription_by_id", fake_get_transcription_by_id)
    monkeypatch.setattr(jobs, "get_company_by_id", fake_get_company_by_id)
    monkeypatch.setattr(jobs, "get_transcriber", lambda: FakeTranscriber())

    result = await jobs._convert_and_transcribe(123)

    assert result.text == "hinted transcript"
