from __future__ import annotations

import argparse
import asyncio
import json
import logging
import mimetypes
import re
import sys

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from config import BEELINE_API_BASE_URL, BEELINE_API_TIMEOUT_SECONDS, UFA_TZ

from .client import BeelineClient
from .models import BeelineAuthConfig, BeelineCallRecord, BeelineSettings

BACKEND_DIR = Path(__file__).resolve().parents[3]
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DownloadRequest:
    token: str
    target_date: date
    output_dir: Path
    base_url: str = BEELINE_API_BASE_URL
    timeout_seconds: float = BEELINE_API_TIMEOUT_SECONDS


@dataclass(slots=True)
class DownloadResult:
    listed_count: int
    matched_count: int
    downloaded_count: int
    output_dir: Path
    manifest_path: Path
    raw_list_path: Path


async def download_records_for_date(request: DownloadRequest) -> DownloadResult:
    output_dir = request.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_list_path = output_dir / "records_raw.json"
    manifest_path = output_dir / "manifest.json"

    async with BeelineClient(
        settings=BeelineSettings(
            base_url=request.base_url,
            timeout_seconds=request.timeout_seconds,
            auth=BeelineAuthConfig(token=request.token),
        )
    ) as client:
        listed_records, raw_items = await _list_records_for_target_date(client, request.target_date)
        raw_list_path.write_text(json.dumps(raw_items, ensure_ascii=False, indent=2), encoding="utf-8")

        manifest: list[dict[str, Any]] = []
        matched_count = 0
        downloaded_count = 0

        for index, record in enumerate(listed_records, start=1):
            detailed_record = await _resolve_record_for_target_date(client, record, request.target_date)
            if detailed_record is None:
                continue

            matched_count += 1
            try:
                downloaded = await _download_record(client, detailed_record)
                extension = _guess_extension(downloaded.content_type, downloaded.filename)
                basename = _build_file_stem(detailed_record, request.target_date)
                destination = _ensure_unique_path(output_dir / f"{basename}{extension}")
                destination.write_bytes(downloaded.content)
                downloaded_count += 1
                manifest.append(
                    {
                        "index": index,
                        "status": "downloaded",
                        "path": str(destination),
                        "size_bytes": len(downloaded.content),
                        "record": detailed_record.model_dump(mode="json"),
                    }
                )
                logger.info("beeline.debug.downloaded", extra={"destination_name": destination.name, "downloaded_count": downloaded_count})
            except Exception as exc:  # pragma: no cover - debug path
                manifest.append(
                    {
                        "index": index,
                        "status": "failed",
                        "error": str(exc),
                        "record": detailed_record.model_dump(mode="json"),
                    }
                )
                logger.warning(
                    "beeline.debug.download_failed",
                    extra={"record_key": _record_primary_key(detailed_record) or "unknown", "detail": str(exc)},
                )

        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return DownloadResult(
        listed_count=len(listed_records),
        matched_count=matched_count,
        downloaded_count=downloaded_count,
        output_dir=output_dir,
        manifest_path=manifest_path,
        raw_list_path=raw_list_path,
    )


async def _list_records_for_target_date(client: BeelineClient, target_date: date) -> tuple[list[BeelineCallRecord], list[dict[str, Any]]]:
    date_from, date_to = _build_target_datetime_range(target_date)
    page_after_id: int | str | None = None
    records: list[BeelineCallRecord] = []
    raw_items: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    while True:
        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
        }
        if page_after_id is not None:
            params["id"] = page_after_id

        payload = await client.list_records_raw(params=params)
        page_items = _extract_record_items(payload)
        if not page_items:
            break

        raw_items.extend(item for item in page_items if isinstance(item, dict))
        page_records = [BeelineCallRecord.model_validate(item) for item in page_items]

        for record in page_records:
            record_key = _record_primary_key(record) or f"record::{record.record_id or record.ext_tracking_id or len(records)}"
            if record_key in seen_keys:
                continue
            seen_keys.add(record_key)
            records.append(record)

        if len(page_records) < 100:
            break

        next_page_id = _next_records_page_id(page_records[-1])
        if next_page_id is None or str(next_page_id) == str(page_after_id):
            break
        page_after_id = next_page_id

    return records, raw_items


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


async def _download_record(client: BeelineClient, record: BeelineCallRecord):
    if record.record_id:
        return await client.download_record_file(record.record_id)
    if record.ext_tracking_id and record.user_id:
        return await client.download_record_file_by_tracking(record.ext_tracking_id, record.user_id)
    raise ValueError("Record does not contain a usable identifier for download.")


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


def _build_target_datetime_range(target_date: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(target_date, time.min, tzinfo=UFA_TZ),
        datetime.combine(target_date, time.max, tzinfo=UFA_TZ),
    )


def _build_file_stem(record: BeelineCallRecord, target_date: date) -> str:
    occurred_at = _record_datetime(record)
    timestamp = occurred_at.astimezone(UFA_TZ).strftime("%Y%m%dT%H%M%S") if occurred_at else target_date.strftime("%Y%m%d")
    phone = re.sub(r"[^0-9]+", "", record.phone_number or record.external_number or "")[-11:] or "unknown"
    record_key = _record_primary_key(record) or "record"
    safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", record_key).strip("._-") or "record"
    return f"{timestamp}_{phone}_{safe_key}"


def _extract_record_items(payload: Any) -> list[Any] | None:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "records", "data", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return None


def _ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _next_records_page_id(record: BeelineCallRecord) -> int | str | None:
    if record.record_id is None:
        return None
    try:
        return int(record.record_id)
    except ValueError:
        return record.record_id


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Beeline call recordings for a specific date.")
    parser.add_argument("--token", required=True, help="Beeline API token for X-MPBX-API-AUTH-TOKEN.")
    parser.add_argument("--date", default="2026-03-30", help="Target date in YYYY-MM-DD format.")
    parser.add_argument(
        "--output-dir",
        default="",
        help="Directory for downloaded files. Defaults to backend/tmp/beeline-debug/<date>.",
    )
    parser.add_argument("--base-url", default=BEELINE_API_BASE_URL, help="Beeline API base URL.")
    parser.add_argument("--timeout-seconds", type=float, default=BEELINE_API_TIMEOUT_SECONDS, help="HTTP timeout in seconds.")
    return parser.parse_args()


async def _async_main() -> int:
    args = _parse_args()
    target_date = date.fromisoformat(args.date)
    output_dir = Path(args.output_dir) if args.output_dir else BACKEND_DIR / "tmp" / "beeline-debug" / target_date.isoformat()
    result = await download_records_for_date(
        DownloadRequest(
            token=args.token,
            target_date=target_date,
            output_dir=output_dir,
            base_url=args.base_url,
            timeout_seconds=args.timeout_seconds,
        )
    )
    sys.stdout.write(
        json.dumps(
            {
                "listed_count": result.listed_count,
                "matched_count": result.matched_count,
                "downloaded_count": result.downloaded_count,
                "output_dir": str(result.output_dir),
                "manifest_path": str(result.manifest_path),
                "raw_list_path": str(result.raw_list_path),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    return 0


def main() -> int:
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
