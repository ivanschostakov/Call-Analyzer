from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import logging
import re

import httpx

from src.app.observability import log_debug, log_error, log_exception, start_timer

from .exceptions import BeelineApiError, BeelineConfigurationError, BeelineResponseFormatError, BeelineTransportError
from .models import (
    BeelineCallRecord,
    BeelineDeleteResult,
    BeelineDownloadedFile,
    BeelineRecordReference,
    BeelineSettings,
    QueryValue,
    ensure_parent_dir,
    serialize_query_params,
)

logger = logging.getLogger(__name__)


class BeelineClient:
    def __init__(
        self,
        *,
        settings: BeelineSettings | None = None,
        http_client: httpx.AsyncClient | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings or BeelineSettings.from_config()
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=self._settings.base_url,
            timeout=self._settings.timeout_seconds,
            transport=transport,
            trust_env=False,
        )

    async def __aenter__(self) -> "BeelineClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def list_records(self, *, params: Mapping[str, QueryValue] | None = None) -> list[BeelineCallRecord]:
        payload = await self.list_records_raw(params=params)
        items = self._extract_record_items(payload)
        if items is None:
            raise BeelineResponseFormatError("GET /records did not return a JSON array.")
        return [BeelineCallRecord.model_validate(item) for item in items]

    async def list_records_raw(self, *, params: Mapping[str, QueryValue] | None = None) -> Any:
        return await self._request_json("GET", "/records", params=params)

    async def get_record(self, record_id: str) -> BeelineCallRecord:
        payload = await self.get_record_raw(record_id)
        if not isinstance(payload, Mapping):
            raise BeelineResponseFormatError(f"GET /v2/records/{record_id} did not return a JSON object.")
        return BeelineCallRecord.model_validate(payload)

    async def get_record_raw(self, record_id: str) -> Any:
        return await self._request_json("GET", f"/v2/records/{record_id}")

    async def get_record_by_tracking(self, ext_tracking_id: str, user_id: str) -> BeelineCallRecord:
        payload = await self.get_record_by_tracking_raw(ext_tracking_id, user_id)
        if not isinstance(payload, Mapping):
            raise BeelineResponseFormatError(
                f"GET /v2/records/{ext_tracking_id}/{user_id} did not return a JSON object."
            )
        return BeelineCallRecord.model_validate(payload)

    async def get_record_by_tracking_raw(self, ext_tracking_id: str, user_id: str) -> Any:
        return await self._request_json("GET", f"/v2/records/{ext_tracking_id}/{user_id}")

    async def download_record(self, record_id: str) -> bytes:
        return await self._request_bytes("GET", f"/v2/records/{record_id}/download")

    async def download_record_by_tracking(self, ext_tracking_id: str, user_id: str) -> bytes:
        return await self._request_bytes("GET", f"/v2/records/{ext_tracking_id}/{user_id}/download")

    async def download_record_file(self, record_id: str) -> BeelineDownloadedFile:
        response = await self._request("GET", f"/v2/records/{record_id}/download")
        return self._build_downloaded_file(response)

    async def download_record_file_by_tracking(self, ext_tracking_id: str, user_id: str) -> BeelineDownloadedFile:
        response = await self._request("GET", f"/v2/records/{ext_tracking_id}/{user_id}/download")
        return self._build_downloaded_file(response)

    async def download_record_to_path(self, record_id: str, destination: str | Path) -> Path:
        path = ensure_parent_dir(Path(destination))
        path.write_bytes(await self.download_record(record_id))
        return path

    async def download_record_by_tracking_to_path(self, ext_tracking_id: str, user_id: str, destination: str | Path) -> Path:
        path = ensure_parent_dir(Path(destination))
        path.write_bytes(await self.download_record_by_tracking(ext_tracking_id, user_id))
        return path

    async def get_record_reference(self, record_id: str) -> BeelineRecordReference:
        payload = await self.get_record_reference_raw(record_id)
        return BeelineRecordReference.from_payload(payload)

    async def get_record_reference_raw(self, record_id: str) -> Any:
        return await self._request_decoded("GET", f"/records/{record_id}/reference")

    async def get_record_reference_by_tracking(self, ext_tracking_id: str, user_id: str) -> BeelineRecordReference:
        payload = await self.get_record_reference_by_tracking_raw(ext_tracking_id, user_id)
        return BeelineRecordReference.from_payload(payload)

    async def get_record_reference_by_tracking_raw(self, ext_tracking_id: str, user_id: str) -> Any:
        return await self._request_decoded("GET", f"/records/{ext_tracking_id}/{user_id}/reference")

    async def delete_record(self, record_id: str) -> BeelineDeleteResult:
        payload = await self.delete_record_raw(record_id)
        return BeelineDeleteResult.from_payload(payload)

    async def delete_record_raw(self, record_id: str) -> Any:
        return await self._request_decoded("DELETE", f"/v2/records/{record_id}", expected_statuses={200, 202, 204})

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryValue] | None = None,
        expected_statuses: set[int] | None = None,
    ) -> Any:
        response = await self._request(method, path, params=params, expected_statuses=expected_statuses)
        try:
            return response.json()
        except ValueError as exc:
            raise BeelineResponseFormatError(f"{method} {path} did not return valid JSON.") from exc

    async def _request_bytes(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryValue] | None = None,
        expected_statuses: set[int] | None = None,
    ) -> bytes:
        response = await self._request(method, path, params=params, expected_statuses=expected_statuses)
        return response.content

    async def _request_decoded(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryValue] | None = None,
        expected_statuses: set[int] | None = None,
    ) -> Any:
        response = await self._request(method, path, params=params, expected_statuses=expected_statuses)
        return self._decode_response(response)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryValue] | None = None,
        expected_statuses: set[int] | None = None,
    ) -> httpx.Response:
        timer = start_timer()
        normalized_params = serialize_query_params(params)
        headers = self._build_auth_headers()
        log_debug(logger, "beeline.request.start", method=method, path=path, params=normalized_params, headers=headers)

        try:
            response = await self._client.request(
                method,
                path,
                params=normalized_params or None,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            log_exception(
                logger,
                "beeline.request.transport_error",
                method=method,
                path=path,
                params=normalized_params,
                duration_ms=timer.elapsed_ms,
            )
            raise BeelineTransportError(str(exc), method=method, path=path) from exc

        allowed_statuses = expected_statuses or set()
        if response.is_error and response.status_code not in allowed_statuses:
            details = self._decode_response(response)
            log_error(
                logger,
                "beeline.request.failed",
                method=method,
                path=path,
                params=normalized_params,
                status_code=response.status_code,
                duration_ms=timer.elapsed_ms,
                details=details,
            )
            raise BeelineApiError(
                f"Beeline API request failed with status {response.status_code}.",
                status_code=response.status_code,
                method=method,
                path=path,
                details=details,
            )

        log_debug(
            logger,
            "beeline.request.success",
            method=method,
            path=path,
            params=normalized_params,
            status_code=response.status_code,
            duration_ms=timer.elapsed_ms,
        )
        return response

    def _build_auth_headers(self) -> dict[str, str]:
        if self._settings.auth is None:
            raise BeelineConfigurationError(
                "Beeline auth is not configured. Pass BeelineSettings(auth=...) with X-MPBX-API-AUTH-TOKEN."
            )
        return self._settings.auth.build_headers()

    @staticmethod
    def _decode_response(response: httpx.Response) -> Any:
        if response.status_code == 204 or not response.content:
            return None

        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type == "application/json":
            try:
                return response.json()
            except ValueError:
                return response.text
        return response.text

    @staticmethod
    def _extract_record_items(payload: Any) -> list[Any] | None:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, Mapping):
            for key in ("items", "records", "data", "result"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return None

    @staticmethod
    def _build_downloaded_file(response: httpx.Response) -> BeelineDownloadedFile:
        content_type = response.headers.get("content-type")
        content_disposition = response.headers.get("content-disposition")
        filename = None
        if content_disposition:
            match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if match:
                filename = match.group(1)
        return BeelineDownloadedFile(content=response.content, content_type=content_type, filename=filename)
