import asyncio
import logging

from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from config import AUDIO_CLEANUP_INTERVAL_SECONDS, AUDIO_RETENTION_DAYS, ufa_now
from src.app.observability import log_exception, log_info
from src.database import get_session
from src.database.crud import (
    list_completed_transcriptions_for_wav_cleanup,
    list_expired_unfavorited_transcriptions,
)
from src.database.models import Transcription

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AudioCleanupResult:
    wav_files_deleted: int = 0
    expired_files_deleted: int = 0
    bytes_freed: int = 0


def _unlink_file(path: Path) -> tuple[bool, int]:
    if not path.exists():
        return False, 0
    size = path.stat().st_size
    path.unlink()
    return True, size


def remove_generated_wav(transcription: Transcription) -> tuple[bool, int]:
    source_path = Path(transcription.source_path)
    wav_path = Path(transcription.file_path)
    if source_path == wav_path or not source_path.exists():
        return False, 0
    return _unlink_file(wav_path)


def remove_all_audio_files(transcription: Transcription) -> tuple[int, int]:
    deleted_count = 0
    bytes_freed = 0
    for path in {Path(transcription.source_path), Path(transcription.file_path)}:
        deleted, size = _unlink_file(path)
        deleted_count += int(deleted)
        bytes_freed += size
    return deleted_count, bytes_freed


async def run_audio_cleanup_once() -> AudioCleanupResult:
    result = AudioCleanupResult()
    older_than = ufa_now() - timedelta(days=AUDIO_RETENTION_DAYS)

    async with get_session() as db:
        completed = await list_completed_transcriptions_for_wav_cleanup(db)
        expired = await list_expired_unfavorited_transcriptions(db, older_than)

    expired_ids = {item.id for item in expired}
    for transcription in completed:
        if transcription.id in expired_ids:
            continue
        deleted, size = await asyncio.to_thread(remove_generated_wav, transcription)
        result.wav_files_deleted += int(deleted)
        result.bytes_freed += size

    for transcription in expired:
        deleted_count, size = await asyncio.to_thread(remove_all_audio_files, transcription)
        result.expired_files_deleted += deleted_count
        result.bytes_freed += size

    log_info(
        logger,
        "audio_cleanup.completed",
        retention_days=AUDIO_RETENTION_DAYS,
        older_than=older_than.isoformat(),
        wav_files_deleted=result.wav_files_deleted,
        expired_files_deleted=result.expired_files_deleted,
        bytes_freed=result.bytes_freed,
    )
    return result


class AudioCleanupRunner:
    def __init__(self, interval_seconds: int = AUDIO_CLEANUP_INTERVAL_SECONDS) -> None:
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop())
        log_info(
            logger,
            "audio_cleanup.runner.started",
            retention_days=AUDIO_RETENTION_DAYS,
            interval_seconds=self._interval_seconds,
        )

    async def stop(self) -> None:
        task = self._task
        stop_event = self._stop_event
        self._task = None
        self._stop_event = None
        if stop_event is not None:
            stop_event.set()
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        log_info(logger, "audio_cleanup.runner.stopped")

    async def _run_loop(self) -> None:
        while True:
            try:
                await run_audio_cleanup_once()
                stop_event = self._stop_event
                if stop_event is None:
                    return
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=self._interval_seconds,
                )
                return
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception:
                log_exception(logger, "audio_cleanup.failed")
                await asyncio.sleep(60)


audio_cleanup_runner = AudioCleanupRunner()


__all__ = [
    "AudioCleanupResult",
    "AudioCleanupRunner",
    "audio_cleanup_runner",
    "remove_all_audio_files",
    "remove_generated_wav",
    "run_audio_cleanup_once",
]
