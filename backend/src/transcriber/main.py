import asyncio
import logging
import time

from pathlib import Path
from typing import Any

from config import LOG_TRANSCRIPTS_ENABLED, OPENAI_API_KEY, OPENAI_TRANSCRIBE_MODEL, USE_LOCAL_TRANSCRIBER, WHISPER_MODEL
from src.app.openai_client import build_openai_async_client
from src.app.observability import log_info, log_warning, start_timer
from src.transcriber.models import Segment, SttResult

try: import whisper
except ImportError: whisper = None


def build_transcription_log_fields(result: SttResult) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "language": result.language,
        "segment_count": len(result.segments),
        "transcript_characters": len(result.text),
    }
    if LOG_TRANSCRIPTS_ENABLED:
        fields["transcript_text"] = result.text
        fields["segments"] = [segment.to_dict() for segment in result.segments]
    return fields


class LocalWhisperTranscriber:
    def __init__(self, model_name: str = WHISPER_MODEL):
        if whisper is None: raise RuntimeError("openai-whisper is not installed")
        if model_name not in whisper.available_models(): raise ValueError(f"Unknown model: {model_name}, try one of: {', '.join(whisper.available_models())}")
        self.__logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        timer = start_timer()
        log_info(self.__logger, "transcriber.model.load.start", model_name=model_name)
        self.__model = whisper.load_model(model_name)
        log_info(self.__logger, "transcriber.model.load.success", model_name=model_name, duration_ms=timer.elapsed_ms)

    @property
    def log(self): return self.__logger

    def _transcribe_sync(self, file_path: Path, prompt: str | None = None) -> SttResult:
        start = time.perf_counter()
        log_info(self.log, "transcriber.transcribe.start", file_path=file_path, hint_prompt_present=bool(prompt), hint_prompt_characters=len(prompt) if prompt else 0)
        if not file_path.exists():
            log_warning(self.log, "transcriber.transcribe.missing_file", file_path=file_path)
            raise FileNotFoundError(f"Audio file does not exist: {file_path}")

        result = SttResult.from_dict(
            self.__model.transcribe(
                str(file_path),
                verbose=True,
                initial_prompt=prompt or None,
            )
        )
        log_info(
            self.log,
            "transcriber.transcribe.success",
            file_path=file_path,
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
            hint_prompt_present=bool(prompt),
            **build_transcription_log_fields(result),
        )
        return result

    async def transcribe(self, file_path: Path, prompt: str | None = None) -> SttResult:
        return await asyncio.to_thread(self._transcribe_sync, file_path, prompt)


class OpenAI4oTranscriber:
    def __init__(self, model_name: str = OPENAI_TRANSCRIBE_MODEL, openai_api_key: str | None = OPENAI_API_KEY):
        if not openai_api_key:
            raise RuntimeError("OpenAI transcription is not configured. Set OPENAI_API_KEY.")
        self.__model_name = model_name
        client = build_openai_async_client(openai_api_key)
        if client is None:
            raise RuntimeError("OpenAI transcription is not configured. Set OPENAI_API_KEY.")
        self.__client = client
        self.__logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        log_info(self.__logger, "transcriber.remote.init", model_name=model_name)

    @property
    def log(self): return self.__logger

    @staticmethod
    def _build_usage_summary(usage) -> dict | None:
        if usage is None:
            return None

        usage_data = usage.model_dump() if hasattr(usage, "model_dump") else usage
        if not isinstance(usage_data, dict):
            return {"raw": str(usage_data)}

        input_token_details = usage_data.get("input_token_details") or {}
        return {
            "type": usage_data.get("type"),
            "seconds": usage_data.get("seconds"),
            "input_count": usage_data.get("input_tokens"),
            "output_count": usage_data.get("output_tokens"),
            "total_count": usage_data.get("total_tokens"),
            "audio_count": input_token_details.get("audio_tokens"),
            "text_count": input_token_details.get("text_tokens"),
        }

    @staticmethod
    def _coerce_response_payload(response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            return response
        if hasattr(response, "model_dump"):
            payload = response.model_dump()
            if isinstance(payload, dict):
                return payload
        return {}

    @staticmethod
    def _coerce_segments(raw_segments: Any) -> list[Segment]:
        if not isinstance(raw_segments, list):
            return []

        segments: list[Segment] = []
        for item in raw_segments:
            if hasattr(item, "model_dump"):
                item = item.model_dump()
            elif hasattr(item, "to_dict") and callable(item.to_dict):
                item = item.to_dict()
            elif hasattr(item, "__dict__"):
                item = {key: value for key, value in vars(item).items() if not key.startswith("_")}
            if isinstance(item, dict):
                segments.append(Segment.from_dict(item))
        return segments

    async def transcribe(self, file_path: Path, prompt: str | None = None) -> SttResult:
        timer = start_timer()
        log_info(
            self.log,
            "transcriber.remote.transcribe.start",
            file_path=file_path,
            model_name=self.__model_name,
            hint_prompt_present=bool(prompt),
            hint_prompt_characters=len(prompt) if prompt else 0,
        )
        if not file_path.exists():
            log_warning(self.log, "transcriber.remote.transcribe.missing_file", file_path=file_path, model_name=self.__model_name)
            raise FileNotFoundError(f"Audio file does not exist: {file_path}")

        request_kwargs: dict[str, Any] = {
            "model": self.__model_name,
        }
        if prompt:
            request_kwargs["prompt"] = prompt

        with file_path.open("rb") as audio_file:
            response = await self.__client.audio.transcriptions.create(
                file=audio_file,
                **request_kwargs,
            )

        payload = self._coerce_response_payload(response)
        text = response if isinstance(response, str) else getattr(response, "text", payload.get("text", ""))
        usage = None if isinstance(response, str) else getattr(response, "usage", None)
        result = SttResult(
            text=str(text).strip(),
            language=str(getattr(response, "language", payload.get("language", "unknown"))).strip() or "unknown",
            segments=self._coerce_segments(getattr(response, "segments", payload.get("segments"))),
        )
        log_info(
            self.log,
            "transcriber.remote.transcribe.success",
            file_path=file_path,
            model_name=self.__model_name,
            duration_ms=timer.elapsed_ms,
            hint_prompt_present=bool(prompt),
            usage=self._build_usage_summary(usage),
            **build_transcription_log_fields(result),
        )
        return result

transcriber: LocalWhisperTranscriber | OpenAI4oTranscriber | None = None


def get_transcriber() -> LocalWhisperTranscriber | OpenAI4oTranscriber:
    global transcriber
    if transcriber is None:
        if USE_LOCAL_TRANSCRIBER:
            transcriber = LocalWhisperTranscriber()
        else:
            transcriber = OpenAI4oTranscriber()
        log_info(
            logging.getLogger(__name__),
            "transcriber.selected",
            implementation=transcriber.__class__.__name__,
            use_local_transcriber=USE_LOCAL_TRANSCRIBER,
        )
    return transcriber
