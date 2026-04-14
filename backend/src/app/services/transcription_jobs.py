import asyncio
import logging
import subprocess

from contextlib import suppress
from datetime import timedelta
from pathlib import Path

from config import LOG_TRANSCRIPTS_ENABLED, TRANSCRIPTION_JOB_CONCURRENCY, ufa_now
from src.app.observability import bind_log_context, log_debug, log_exception, log_info, log_state_change, log_warning, reset_log_context, start_timer
from src.app.modules.uploads.helpers import convert_to_wav
from src.database import get_session
from src.database.crud import (
    claim_next_queued_transcription,
    get_company_by_id,
    get_transcription_by_id,
    requeue_processing_transcriptions,
    touch_processing_transcription,
    update_transcription,
)
from src.database.schemas import TranscriptionSegmentRead, TranscriptionUpdate
from src.enums import TranscriptionStatus
from src.transcriber import get_transcriber

from .auto_analysis import auto_analyze_beeline_transcription

logger = logging.getLogger(__name__)
PROCESSING_STALE_AFTER_SECONDS = 300
PROCESSING_HEARTBEAT_INTERVAL_SECONDS = 15

async def requeue_stuck_transcription_jobs(stale_after_seconds: int = PROCESSING_STALE_AFTER_SECONDS) -> int:
    timer = start_timer()
    older_than = ufa_now() - timedelta(seconds=stale_after_seconds)
    log_debug(logger, "transcription.jobs.requeue.start", older_than=older_than.isoformat(), stale_after_seconds=stale_after_seconds)
    async with get_session() as db: recovered = await requeue_processing_transcriptions(db, older_than=older_than)
    finish_logger = log_info if recovered else log_debug
    finish_logger(logger, "transcription.jobs.requeue.finish", recovered=recovered, duration_ms=timer.elapsed_ms)
    return recovered


async def run_transcription_jobs_once() -> bool:
    log_debug(logger, "transcription.jobs.claim.start")
    async with get_session() as db: transcription = await claim_next_queued_transcription(db)
    if transcription is None:
        log_debug(logger, "transcription.jobs.claim.empty")
        return False

    log_debug(
        logger,
        "transcription.jobs.claim.success",
        transcription_id=transcription.id,
        company_id=transcription.company_id,
        file_id=transcription.file_id,
        status=transcription.status,
    )
    await _process_claimed_transcription(transcription.id)
    return True


async def _process_claimed_transcription(transcription_id: int) -> None:
    token = bind_log_context(job_type="transcription", transcription_id=transcription_id)
    timer = start_timer()
    heartbeat_task = asyncio.create_task(_heartbeat_processing_transcription(transcription_id))
    log_debug(logger, "transcription.job.start", transcription_id=transcription_id)
    try:
        stt_result = await _convert_and_transcribe(transcription_id)
        async with get_session() as db:
            current = await get_transcription_by_id(db, transcription_id)
            if current is None:
                log_warning(logger, "transcription.job.missing_record", transcription_id=transcription_id)
                return

            await update_transcription(
                db,
                current,
                TranscriptionUpdate(
                    status=TranscriptionStatus.COMPLETED,
                    language=stt_result.language,
                    text=stt_result.text,
                    segments=[TranscriptionSegmentRead.model_validate(segment.to_dict()) for segment in stt_result.segments],
                    error_message=None,
                    transcribed_at=ufa_now(),
                ),
            )
            log_state_change(
                logger,
                "transcription",
                transcription_id,
                TranscriptionStatus.PROCESSING.value,
                TranscriptionStatus.COMPLETED.value,
                language=stt_result.language,
                segment_count=len(stt_result.segments),
                transcript_text=stt_result.text if LOG_TRANSCRIPTS_ENABLED else None,
            )
            log_info(
                logger,
                "transcription.job.completed",
                transcription_id=transcription_id,
                language=stt_result.language,
                segment_count=len(stt_result.segments),
                transcript_text=stt_result.text if LOG_TRANSCRIPTS_ENABLED else None,
                duration_ms=timer.elapsed_ms,
            )
        try:
            did_create_analysis = await auto_analyze_beeline_transcription(transcription_id)
            if did_create_analysis:
                log_debug(logger, "transcription.job.auto_analysis.completed", transcription_id=transcription_id)
        except Exception as exc:
            log_exception(logger, "transcription.job.auto_analysis.failed", transcription_id=transcription_id, detail=str(exc))
    except FileNotFoundError as exc:
        log_warning(logger, "transcription.job.file_missing", transcription_id=transcription_id, detail=str(exc))
        await _mark_failed(transcription_id, str(exc))
        return
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or "Could not convert file to WAV."
        log_warning(logger, "transcription.job.conversion_failed", transcription_id=transcription_id, detail=detail)
        await _mark_failed(transcription_id, detail)
        return
    except RuntimeError as exc:
        log_warning(logger, "transcription.job.runtime_failed", transcription_id=transcription_id, detail=str(exc))
        await _mark_failed(transcription_id, str(exc))
        return
    except Exception as exc:
        log_exception(logger, "transcription.job.failed", transcription_id=transcription_id, detail=str(exc))
        await _mark_failed(transcription_id, f"Unexpected transcription failure: {exc}")
        return
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError): await heartbeat_task
        log_debug(logger, "transcription.job.finish", transcription_id=transcription_id, duration_ms=timer.elapsed_ms)
        reset_log_context(token)

    


async def _convert_and_transcribe(transcription_id: int):
    timer = start_timer()
    hint_prompt: str | None = None
    async with get_session() as db:
        transcription = await get_transcription_by_id(db, transcription_id)
        if transcription is None: raise FileNotFoundError("Transcription record no longer exists.")
        company = await get_company_by_id(db, transcription.company_id)

        source_path = Path(transcription.source_path)
        wav_path = Path(transcription.file_path)
        hint_prompt = (company.transcription_hint_prompt or "").strip() or None if company is not None else None
        log_debug(
            logger,
            "transcription.job.paths.loaded",
            transcription_id=transcription_id,
            source_path=source_path,
            wav_path=wav_path,
            source_exists=source_path.exists(),
            wav_exists=wav_path.exists(),
            hint_prompt_present=bool(hint_prompt),
            hint_prompt_characters=len(hint_prompt) if hint_prompt else 0,
        )

    if not source_path.exists() and not wav_path.exists(): raise FileNotFoundError("Uploaded audio was not found.")

    if not wav_path.exists():
        log_debug(logger, "transcription.job.convert.required", transcription_id=transcription_id, source_path=source_path, wav_path=wav_path)
        await asyncio.to_thread(convert_to_wav, source_path, wav_path)

    stt_result = await get_transcriber().transcribe(wav_path, prompt=hint_prompt)
    log_debug(
        logger,
        "transcription.job.transcribe.finish",
        transcription_id=transcription_id,
        duration_ms=timer.elapsed_ms,
        language=stt_result.language,
        segment_count=len(stt_result.segments),
        hint_prompt_present=bool(hint_prompt),
        transcript_text=stt_result.text if LOG_TRANSCRIPTS_ENABLED else None,
    )
    return stt_result


async def _mark_failed(transcription_id: int, detail: str) -> None:
    async with get_session() as db:
        transcription = await get_transcription_by_id(db, transcription_id)
        if transcription is None:
            log_warning(logger, "transcription.job.fail_missing_record", transcription_id=transcription_id, detail=detail)
            return

        await update_transcription(
            db,
            transcription,
            TranscriptionUpdate(
                status=TranscriptionStatus.FAILED,
                error_message=detail,
            ),
        )
        log_state_change(
            logger,
            "transcription",
            transcription_id,
            transcription.status,
            TranscriptionStatus.FAILED.value,
            detail=detail,
        )
        log_warning(logger, "transcription.job.mark_failed", transcription_id=transcription_id, detail=detail)


async def _heartbeat_processing_transcription(transcription_id: int) -> None:
    while True:
        await asyncio.sleep(PROCESSING_HEARTBEAT_INTERVAL_SECONDS)
        async with get_session() as db:
            keep_going = await touch_processing_transcription(db, transcription_id)
        if not keep_going:
            log_debug(logger, "transcription.job.heartbeat.stop", transcription_id=transcription_id)
            return
        log_debug(logger, "transcription.job.heartbeat", transcription_id=transcription_id)


class TranscriptionJobRunner:
    def __init__(self, poll_interval_seconds: float = 1.0, concurrency: int = TRANSCRIPTION_JOB_CONCURRENCY):
        self._poll_interval_seconds = poll_interval_seconds
        self._concurrency = max(int(concurrency), 1)
        self._tasks: list[asyncio.Task] = []
        self._state_lock = asyncio.Lock()
        self._wakeup_event: asyncio.Event | None = None
        self._stop_event: asyncio.Event | None = None

    async def start(self) -> None:
        async with self._state_lock:
            if any(not task.done() for task in self._tasks):
                log_debug(logger, "transcription.runner.start.skipped", reason="already_running")
                return

            log_info(
                logger,
                "transcription.runner.start",
                poll_interval_seconds=self._poll_interval_seconds,
                concurrency=self._concurrency,
            )
            recovered = await requeue_stuck_transcription_jobs()
            self._wakeup_event = asyncio.Event()
            self._stop_event = asyncio.Event()
            self._tasks = [asyncio.create_task(self._run_loop(worker_index)) for worker_index in range(self._concurrency)]
            log_info(logger, "transcription.runner.started", recovered=recovered, worker_count=len(self._tasks))

    async def stop(self) -> None:
        async with self._state_lock:
            tasks = self._tasks
            stop_event = self._stop_event
            wakeup_event = self._wakeup_event
            self._tasks = []
            self._stop_event = None
            self._wakeup_event = None

        log_info(logger, "transcription.runner.stop")
        if stop_event is not None: stop_event.set()
        if wakeup_event is not None: wakeup_event.set()
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task
        log_info(logger, "transcription.runner.stopped", worker_count=len(tasks))

    async def wake_up(self) -> None:
        if self._wakeup_event is not None:
            self._wakeup_event.set()
            log_debug(logger, "transcription.runner.wakeup")

    async def _run_loop(self, worker_index: int) -> None:
        while True:
            try:
                if self._stop_event is not None and self._stop_event.is_set():
                    log_debug(logger, "transcription.runner.loop.stop_requested", worker_index=worker_index)
                    return

                if worker_index == 0:
                    recovered = await requeue_stuck_transcription_jobs()
                    if recovered:
                        log_debug(logger, "transcription.runner.loop.recovered_jobs", worker_index=worker_index, recovered=recovered)
                        continue

                did_work = await run_transcription_jobs_once()
                if did_work:
                    log_debug(logger, "transcription.runner.loop.work_processed", worker_index=worker_index)
                    continue

                wakeup_event = self._wakeup_event
                if wakeup_event is None:
                    log_debug(logger, "transcription.runner.loop.no_wakeup_event", worker_index=worker_index)
                    return

                try:
                    await asyncio.wait_for(wakeup_event.wait(), timeout=self._poll_interval_seconds)
                    log_debug(logger, "transcription.runner.loop.woken", worker_index=worker_index)
                except asyncio.TimeoutError: continue
                finally: wakeup_event.clear()
            except asyncio.CancelledError:
                log_debug(logger, "transcription.runner.loop.cancelled", worker_index=worker_index)
                raise
            except Exception:
                log_exception(logger, "transcription.runner.loop.failed", worker_index=worker_index)
                await asyncio.sleep(self._poll_interval_seconds)


transcription_job_runner = TranscriptionJobRunner()

async def enqueue_transcription_job(transcription_id: int) -> bool:
    log_debug(logger, "transcription.job.enqueue", transcription_id=transcription_id)
    await transcription_job_runner.wake_up()
    return True
