import logging
from types import SimpleNamespace

import pytest

from conftest import event_records


def test_get_transcriber_selects_local_when_enabled(monkeypatch, caplog) -> None:
    from src.transcriber import main as transcriber_main

    class FakeLocal:
        pass

    class FakeRemote:
        pass

    monkeypatch.setattr(transcriber_main, "LocalWhisperTranscriber", FakeLocal)
    monkeypatch.setattr(transcriber_main, "OpenAI4oTranscriber", FakeRemote)
    monkeypatch.setattr(transcriber_main, "USE_LOCAL_TRANSCRIBER", True)
    monkeypatch.setattr(transcriber_main, "transcriber", None)

    caplog.set_level(logging.INFO)
    transcriber = transcriber_main.get_transcriber()

    assert isinstance(transcriber, FakeLocal)
    selected_record = event_records(caplog, "transcriber.selected")[0]
    assert selected_record.event_fields["implementation"] == "FakeLocal"


def test_get_transcriber_selects_remote_when_disabled(monkeypatch, caplog) -> None:
    from src.transcriber import main as transcriber_main

    class FakeLocal:
        pass

    class FakeRemote:
        pass

    monkeypatch.setattr(transcriber_main, "LocalWhisperTranscriber", FakeLocal)
    monkeypatch.setattr(transcriber_main, "OpenAI4oTranscriber", FakeRemote)
    monkeypatch.setattr(transcriber_main, "USE_LOCAL_TRANSCRIBER", False)
    monkeypatch.setattr(transcriber_main, "transcriber", None)

    caplog.set_level(logging.INFO)
    transcriber = transcriber_main.get_transcriber()

    assert isinstance(transcriber, FakeRemote)
    selected_record = event_records(caplog, "transcriber.selected")[0]
    assert selected_record.event_fields["implementation"] == "FakeRemote"


@pytest.mark.asyncio
async def test_openai_4o_transcriber_maps_json_response(monkeypatch, tmp_path, caplog) -> None:
    from src.transcriber import main as transcriber_main

    seen: dict[str, object] = {}

    class FakeAudioTranscriptions:
        async def create(self, *, file, model, prompt=None):
            seen["prompt"] = prompt
            return SimpleNamespace(
                text="remote transcript text",
                usage=SimpleNamespace(model_dump=lambda: {"type": "tokens", "total_tokens": 42}),
            )

    fake_client = SimpleNamespace(audio=SimpleNamespace(transcriptions=FakeAudioTranscriptions()))

    monkeypatch.setattr(transcriber_main, "build_openai_async_client", lambda api_key: fake_client)

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"wav-data")

    caplog.set_level(logging.INFO)
    transcriber = transcriber_main.OpenAI4oTranscriber(model_name="gpt-4o-transcribe", openai_api_key="test-key")
    result = await transcriber.transcribe(audio_path, prompt="company glossary")

    assert result.text == "remote transcript text"
    assert result.language == "unknown"
    assert result.segments == []
    assert seen["prompt"] == "company glossary"

    success_record = event_records(caplog, "transcriber.remote.transcribe.success")[0]
    assert success_record.event_fields["model_name"] == "gpt-4o-transcribe"
    assert success_record.event_fields["usage"]["total_count"] == 42


@pytest.mark.asyncio
async def test_local_whisper_transcriber_passes_initial_prompt(monkeypatch, tmp_path) -> None:
    from src.transcriber import main as transcriber_main

    seen: dict[str, object] = {}

    class FakeModel:
        def transcribe(self, file_path, verbose=True, initial_prompt=None):
            seen["file_path"] = file_path
            seen["verbose"] = verbose
            seen["initial_prompt"] = initial_prompt
            return {
                "text": "local transcript text",
                "language": "ru",
                "segments": [],
            }

    class FakeWhisperModule:
        @staticmethod
        def available_models():
            return ["tiny"]

        @staticmethod
        def load_model(model_name):
            assert model_name == "tiny"
            return FakeModel()

    monkeypatch.setattr(transcriber_main, "whisper", FakeWhisperModule())

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"wav-data")

    transcriber = transcriber_main.LocalWhisperTranscriber(model_name="tiny")
    result = await transcriber.transcribe(audio_path, prompt="company glossary")

    assert result.text == "local transcript text"
    assert result.language == "ru"
    assert seen["initial_prompt"] == "company glossary"
