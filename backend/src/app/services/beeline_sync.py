import asyncio
import hashlib
import logging
import mimetypes
import re

from contextlib import suppress
from datetime import date, datetime, time, timedelta
from pathlib import Path

from config import BEELINE_API_BASE_URL, BEELINE_API_TIMEOUT_SECONDS, COMPANIES_UPLOAD_DIR, UFA_TZ, ufa_now
from src.app.observability import bind_log_context, log_debug, log_exception, log_info, log_warning, reset_log_context, start_timer
from src.database import get_session
from src.database.crud import (
    create_transcription,
    get_company_by_id,
    get_transcription_by_company_id_and_file_id,
    list_companies_with_beeline_auto_export_enabled,
    update_company,
)
from src.database.schemas import CompanyUpdate, TranscriptionCreate
from src.enums import TranscriptionStatus
from src.integrations.beeline import BeelineAuthConfig, BeelineCallRecord, BeelineClient, BeelineSettings

from .transcription_jobs import enqueue_transcription_job

logger = logging.getLogger(__name__)
BEELINE_SYNC_STATUS_RUNNING = "running"
BEELINE_SYNC_STATUS_SUCCESS = "success"
BEELINE_SYNC_STATUS_FAILED = "failed"
BEELINE_MIN_DURATION_SECONDS = 120
BEELINE_AUTO_SYNC_INTERVAL_HOURS = 2
BEELINE_SYNC_KIND_MANUAL = "manual"
BEELINE_SYNC_KIND_AUTO = "auto"


async def run_due_beeline_syncs(target_date: date | None = None, reference_time: datetime | None = None) -> int:
    effective_reference_time = _coerce_reference_time(reference_time)
    effective_target_date = target_date or effective_reference_time.date()
    timer = start_timer()
    log_debug(
        logger,
        "beeline.sync.run_due.start",
        target_date=effective_target_date.isoformat(),
        reference_time=effective_reference_time.isoformat(),
    )

    async with get_session() as db:
        companies = await list_companies_with_beeline_auto_export_enabled(db)

    synced_count = 0
    for company in companies:
        if not _company_sync_due(company, effective_reference_time):
            continue
        await sync_company_beeline_recordings(company.id, effective_target_date, sync_kind=BEELINE_SYNC_KIND_AUTO)
        synced_count += 1

    finish_logger = log_info if synced_count else log_debug
    finish_logger(
        logger,
        "beeline.sync.run_due.finish",
        target_date=effective_target_date.isoformat(),
        reference_time=effective_reference_time.isoformat(),
        synced_count=synced_count,
        duration_ms=timer.elapsed_ms,
    )
    return synced_count


async def sync_company_beeline_recordings(company_id: int, target_date: date, *, sync_kind: str = BEELINE_SYNC_KIND_MANUAL) -> int:
    token = bind_log_context(job_type="beeline_sync", company_id=company_id, target_date=target_date.isoformat(), sync_kind=sync_kind)
    timer = start_timer()
    log_debug(logger, "beeline.sync.company.start", company_id=company_id, target_date=target_date.isoformat(), sync_kind=sync_kind)
    try:
        async with get_session() as db:
            company = await get_company_by_id(db, company_id)
            if company is None:
                log_warning(logger, "beeline.sync.company.missing_company", company_id=company_id)
                return 0
            if not company.beeline_auto_export_enabled or not (company.beeline_api_token or "").strip():
                log_debug(logger, "beeline.sync.company.skipped_disabled", company_id=company_id)
                return 0

            company = await update_company(
                db,
                company,
                _build_sync_company_update(
                    sync_kind=sync_kind,
                    target_date=target_date,
                    started_at=ufa_now(),
                    finished_at=None,
                    status=BEELINE_SYNC_STATUS_RUNNING,
                    error=None,
                ),
            )
            token_value = company.beeline_api_token or ""
            owner_id = company.owner_id

        async with BeelineClient(
            settings=BeelineSettings(
                base_url=BEELINE_API_BASE_URL,
                timeout_seconds=BEELINE_API_TIMEOUT_SECONDS,
                auth=BeelineAuthConfig(token=token_value),
            )
        ) as client:
            imported_count = await _sync_company_records(client=client, company_id=company_id, owner_id=owner_id, target_date=target_date)

        async with get_session() as db:
            company = await get_company_by_id(db, company_id)
            if company is not None:
                await update_company(
                    db,
                    company,
                    _build_sync_company_update(
                        sync_kind=sync_kind,
                        target_date=target_date,
                        started_at=_get_sync_started_at(company, sync_kind),
                        finished_at=ufa_now(),
                        status=BEELINE_SYNC_STATUS_SUCCESS,
                        error=None,
                    ),
                )
        log_info(logger, "beeline.sync.company.success", company_id=company_id, target_date=target_date.isoformat(), imported_count=imported_count, duration_ms=timer.elapsed_ms, sync_kind=sync_kind)
        return imported_count
    except Exception as exc:
        detail = _truncate_error(str(exc))
        async with get_session() as db:
            company = await get_company_by_id(db, company_id)
            if company is not None:
                await update_company(
                    db,
                    company,
                    _build_sync_company_update(
                        sync_kind=sync_kind,
                        target_date=target_date,
                        started_at=_get_sync_started_at(company, sync_kind),
                        finished_at=ufa_now(),
                        status=BEELINE_SYNC_STATUS_FAILED,
                        error=detail,
                    ),
                )
        log_exception(logger, "beeline.sync.company.failed", company_id=company_id, target_date=target_date.isoformat(), detail=detail, sync_kind=sync_kind)
        return 0
    finally:
        log_debug(logger, "beeline.sync.company.finish", company_id=company_id, target_date=target_date.isoformat(), duration_ms=timer.elapsed_ms, sync_kind=sync_kind)
        reset_log_context(token)


async def sync_company_beeline_recordings_range(company_id: int, date_from: date, date_to: date) -> int:
    total_imported = 0
    current_date = date_from
    while current_date <= date_to:
        total_imported += await sync_company_beeline_recordings(company_id, current_date, sync_kind=BEELINE_SYNC_KIND_MANUAL)
        current_date += timedelta(days=1)
    return total_imported


async def _sync_company_records(*, client: BeelineClient, company_id: int, owner_id: int, target_date: date) -> int:
    records = await _list_records_for_target_date(client, target_date)
    imported_count = 0
    for record in records:
        detailed_record = await _resolve_record_for_target_date(client, record, target_date)
        if detailed_record is None:
            continue
        did_import = await _import_record_if_missing(
            client=client,
            company_id=company_id,
            owner_id=owner_id,
            target_date=target_date,
            record=detailed_record,
        )
        if did_import:
            imported_count += 1
    return imported_count


async def _list_records_for_target_date(client: BeelineClient, target_date: date) -> list[BeelineCallRecord]:
    date_from, date_to = _build_target_datetime_range(target_date)
    page_after_id: int | str | None = None
    records: list[BeelineCallRecord] = []
    seen_keys: set[str] = set()

    while True:
        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
        }
        if page_after_id is not None:
            params["id"] = page_after_id

        page = await client.list_records(params=params)
        if not page:
            break

        for record in page:
            record_key = _record_primary_key(record) or f"record::{record.record_id or record.ext_tracking_id or len(records)}"
            if record_key in seen_keys:
                continue
            seen_keys.add(record_key)
            records.append(record)

        if len(page) < 100:
            break

        next_page_id = _next_records_page_id(page[-1])
        if next_page_id is None or str(next_page_id) == str(page_after_id):
            break
        page_after_id = next_page_id

    return records


async def _resolve_record_for_target_date(client: BeelineClient, record: BeelineCallRecord, target_date: date) -> BeelineCallRecord | None:
    if _record_matches_target_date(record, target_date):
        return record

    if _record_datetime(record) is not None:
        return None

    if record.record_id:
        detailed_record = await client.get_record(record.record_id)
        if _record_matches_target_date(detailed_record, target_date):
            return detailed_record
        return None

    if record.ext_tracking_id and record.user_id:
        detailed_record = await client.get_record_by_tracking(record.ext_tracking_id, record.user_id)
        if _record_matches_target_date(detailed_record, target_date):
            return detailed_record

    return None


async def _import_record_if_missing(*, client: BeelineClient, company_id: int, owner_id: int, target_date: date, record: BeelineCallRecord) -> bool:
    record_key = _record_primary_key(record)
    if record_key is None:
        log_warning(logger, "beeline.sync.record.skipped_missing_identifier", company_id=company_id, target_date=target_date.isoformat())
        return False

    if _record_is_too_short(record):
        log_debug(
            logger,
            "beeline.sync.record.skipped_short_duration",
            company_id=company_id,
            target_date=target_date.isoformat(),
            record_key=record_key,
            duration_seconds=record.duration_seconds,
            min_duration_seconds=BEELINE_MIN_DURATION_SECONDS,
        )
        return False

    file_id = _build_company_file_id(record_key)

    async with get_session() as db:
        existing = await get_transcription_by_company_id_and_file_id(db, company_id, file_id)
        if existing is not None:
            log_debug(logger, "beeline.sync.record.skipped_existing", company_id=company_id, file_id=file_id, record_key=record_key)
            return False

    if record.record_id:
        downloaded = await client.download_record_file(record.record_id)
    elif record.ext_tracking_id and record.user_id:
        downloaded = await client.download_record_file_by_tracking(record.ext_tracking_id, record.user_id)
    else:
        return False

    extension = _guess_extension(downloaded.content_type, downloaded.filename)
    original_filename = _build_original_filename(record, target_date, extension)
    call_started_at = _record_datetime(record)
    company_dir = COMPANIES_UPLOAD_DIR / str(company_id)
    company_dir.mkdir(parents=True, exist_ok=True)
    source_path = company_dir / f"{file_id}__source{extension}"
    wav_path = company_dir / f"{file_id}.flac"

    try:
        source_path.write_bytes(downloaded.content)
        async with get_session() as db:
            transcription = await create_transcription(
                db,
                TranscriptionCreate(
                    company_id=company_id,
                    uploaded_by_user_id=owner_id,
                    file_id=file_id,
                    original_filename=original_filename[:255],
                    source_path=str(source_path),
                    file_path=str(wav_path),
                    status=TranscriptionStatus.QUEUED,
                    call_started_at=call_started_at,
                ),
            )
        await enqueue_transcription_job(transcription.id)
        log_info(
            logger,
            "beeline.sync.record.imported",
            company_id=company_id,
            transcription_id=transcription.id,
            file_id=file_id,
            original_filename=original_filename,
            call_started_at=call_started_at.isoformat() if call_started_at else None,
        )
        return True
    except Exception:
        source_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)
        raise


def _company_sync_due(company, reference: date | datetime | None = None) -> bool:
    if not company.beeline_auto_export_enabled or not (company.beeline_api_token or "").strip():
        return False
    reference_time = _coerce_reference_time(reference)
    target_date = reference_time.date()
    current_window_start = _current_sync_window_start(reference_time)
    if company.beeline_last_auto_sync_target_date is None or company.beeline_last_auto_sync_started_at is None:
        return True
    if company.beeline_last_auto_sync_target_date < target_date:
        return True
    last_started_at = _coerce_reference_time(company.beeline_last_auto_sync_started_at)
    return last_started_at < current_window_start


def _get_sync_started_at(company, sync_kind: str) -> datetime | None:
    if sync_kind == BEELINE_SYNC_KIND_AUTO:
        return company.beeline_last_auto_sync_started_at
    return company.beeline_last_sync_started_at


def _build_sync_company_update(
    *,
    sync_kind: str,
    target_date: date,
    started_at: datetime | None,
    finished_at: datetime | None,
    status: str | None,
    error: str | None,
) -> CompanyUpdate:
    if sync_kind == BEELINE_SYNC_KIND_AUTO:
        return CompanyUpdate(
            beeline_last_auto_sync_target_date=target_date,
            beeline_last_auto_sync_started_at=started_at,
            beeline_last_auto_sync_finished_at=finished_at,
            beeline_last_auto_sync_status=status,
            beeline_last_auto_sync_error=error,
        )
    return CompanyUpdate(
        beeline_last_sync_target_date=target_date,
        beeline_last_sync_started_at=started_at,
        beeline_last_sync_finished_at=finished_at,
        beeline_last_sync_status=status,
        beeline_last_sync_error=error,
    )


def _record_matches_target_date(record: BeelineCallRecord, target_date: date) -> bool:
    occurred_at = _record_datetime(record)
    if occurred_at is None:
        return False
    return occurred_at.astimezone(UFA_TZ).date() == target_date


def _record_datetime(record: BeelineCallRecord) -> datetime | None:
    occurred_at = record.started_at or record.ended_at
    if occurred_at is None:
        return None
    if occurred_at.tzinfo is None:
        return occurred_at.replace(tzinfo=UFA_TZ)
    return occurred_at


def _record_primary_key(record: BeelineCallRecord) -> str | None:
    if record.record_id:
        return record.record_id
    if record.ext_tracking_id and record.user_id:
        return f"{record.ext_tracking_id}_{record.user_id}"
    return None


def _build_company_file_id(record_key: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", record_key).strip("._-")
    candidate = f"beeline_{normalized}" if normalized else ""
    if candidate and len(candidate) <= 64:
        return candidate
    digest = hashlib.sha256(record_key.encode("utf-8")).hexdigest()[:24]
    return f"beeline_{digest}"


def _build_target_datetime_range(target_date: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(target_date, time.min, tzinfo=UFA_TZ),
        datetime.combine(target_date, time.max, tzinfo=UFA_TZ),
    )


def _next_records_page_id(record: BeelineCallRecord) -> int | str | None:
    if record.record_id is None:
        return None
    try:
        return int(record.record_id)
    except ValueError:
        return record.record_id


def _record_is_too_short(record: BeelineCallRecord) -> bool:
    return record.duration_seconds is not None and record.duration_seconds < BEELINE_MIN_DURATION_SECONDS


def _guess_extension(content_type: str | None, filename: str | None) -> str:
    if filename:
        suffix = Path(filename).suffix
        if suffix:
            return suffix.lower()
    if content_type:
        suffix = mimetypes.guess_extension(content_type.split(";", 1)[0].strip().lower())
        if suffix:
            return suffix
    return ".bin"


def _build_original_filename(record: BeelineCallRecord, target_date: date, extension: str) -> str:
    phone = re.sub(r"[^0-9]+", "", record.phone_number or record.external_number or "")[-11:]
    record_key = _record_primary_key(record) or "record"
    safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", record_key).strip("._-") or "record"
    pieces = ["beeline", target_date.isoformat()]
    if phone:
        pieces.append(phone)
    pieces.append(safe_key)
    return "_".join(pieces) + extension


def _truncate_error(detail: str, limit: int = 2000) -> str:
    if len(detail) <= limit:
        return detail
    return detail[: limit - 3].rstrip() + "..."


def _coerce_reference_time(reference: date | datetime | None) -> datetime:
    if reference is None:
        return ufa_now()
    if isinstance(reference, datetime):
        if reference.tzinfo is None:
            return reference.replace(tzinfo=UFA_TZ)
        return reference.astimezone(UFA_TZ)
    return datetime.combine(reference, time.min, tzinfo=UFA_TZ)


def _current_sync_window_start(reference: date | datetime | None = None) -> datetime:
    localized = _coerce_reference_time(reference).astimezone(UFA_TZ)
    hour = localized.hour - (localized.hour % BEELINE_AUTO_SYNC_INTERVAL_HOURS)
    return localized.replace(hour=hour, minute=0, second=0, microsecond=0)


def _next_sync_check(reference: date | datetime | None = None) -> datetime:
    current_window_start = _current_sync_window_start(reference)
    return current_window_start + timedelta(hours=BEELINE_AUTO_SYNC_INTERVAL_HOURS)


class BeelineSyncRunner:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._state_lock = asyncio.Lock()
        self._stop_event: asyncio.Event | None = None

    async def start(self) -> None:
        async with self._state_lock:
            if self._task is not None and not self._task.done():
                log_info(logger, "beeline.sync.runner.start.skipped", reason="already_running")
                return

            self._stop_event = asyncio.Event()
            self._task = asyncio.create_task(self._run_loop())
            log_info(logger, "beeline.sync.runner.started")

    async def stop(self) -> None:
        async with self._state_lock:
            task = self._task
            stop_event = self._stop_event
            self._task = None
            self._stop_event = None

        log_info(logger, "beeline.sync.runner.stop")
        if stop_event is not None:
            stop_event.set()
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        log_info(logger, "beeline.sync.runner.stopped")

    async def _run_loop(self) -> None:
        while True:
            try:
                await run_due_beeline_syncs()
                stop_event = self._stop_event
                if stop_event is None:
                    return

                now = ufa_now()
                sleep_seconds = max((_next_sync_check(now) - now).total_seconds(), 1.0)
                log_info(logger, "beeline.sync.runner.sleep", sleep_seconds=round(sleep_seconds, 3))
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=sleep_seconds)
                    log_info(logger, "beeline.sync.runner.woken_for_stop")
                    return
                except asyncio.TimeoutError:
                    continue
            except asyncio.CancelledError:
                log_info(logger, "beeline.sync.runner.cancelled")
                raise
            except Exception:
                log_exception(logger, "beeline.sync.runner.failed")
                await asyncio.sleep(5)


beeline_sync_runner = BeelineSyncRunner()

__all__ = [
    "BEELINE_SYNC_STATUS_FAILED",
    "BEELINE_SYNC_STATUS_RUNNING",
    "BEELINE_SYNC_STATUS_SUCCESS",
    "BeelineSyncRunner",
    "beeline_sync_runner",
    "run_due_beeline_syncs",
    "sync_company_beeline_recordings",
    "sync_company_beeline_recordings_range",
]
