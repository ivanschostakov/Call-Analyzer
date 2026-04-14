from datetime import date, datetime, timezone

from fastapi import HTTPException
from openai import OpenAIError
from starlette import status

from src.app.modules.common import conflict_exception
from src.app.modules.companies.schemas import CompanyBeelineIntegrationRead, CompanyVectorStoreFileBatchRead, CompanyVectorStoreFileRead, CompanyVectorStoreRead


def build_company_vector_store_read(company_id: int, vector_store_id: str | None) -> CompanyVectorStoreRead:
    return CompanyVectorStoreRead(company_id=company_id, vector_store_id=vector_store_id)


def _resolve_last_beeline_sync(company) -> tuple[datetime | None, date | None, datetime | None, datetime | None, str | None, str | None]:
    manual_marker = company.beeline_last_sync_finished_at or company.beeline_last_sync_started_at
    auto_marker = company.beeline_last_auto_sync_finished_at or company.beeline_last_auto_sync_started_at

    if auto_marker and (manual_marker is None or auto_marker >= manual_marker):
        return (
            auto_marker,
            company.beeline_last_auto_sync_target_date,
            company.beeline_last_auto_sync_started_at,
            company.beeline_last_auto_sync_finished_at,
            company.beeline_last_auto_sync_status,
            company.beeline_last_auto_sync_error,
        )

    return (
        manual_marker,
        company.beeline_last_sync_target_date,
        company.beeline_last_sync_started_at,
        company.beeline_last_sync_finished_at,
        company.beeline_last_sync_status,
        company.beeline_last_sync_error,
    )


def build_company_beeline_integration_read(company) -> CompanyBeelineIntegrationRead:
    token = (company.beeline_api_token or "").strip()
    token_hint = None
    if token:
        visible_tail = token[-4:] if len(token) >= 4 else token
        token_hint = f"••••{visible_tail}"

    _, last_sync_target_date, last_sync_started_at, last_sync_finished_at, last_sync_status, last_sync_error = _resolve_last_beeline_sync(company)

    return CompanyBeelineIntegrationRead(
        company_id=company.id,
        enabled=bool(company.beeline_auto_export_enabled and token),
        has_token=bool(token),
        token_hint=token_hint,
        analysis_template_id=company.beeline_auto_analysis_template_id,
        last_sync_target_date=last_sync_target_date,
        last_sync_started_at=last_sync_started_at,
        last_sync_finished_at=last_sync_finished_at,
        last_sync_status=last_sync_status,
        last_sync_error=last_sync_error,
    )


def build_company_vector_store_file_read(
        *,
        file_id: str,
        filename: str,
        status_name: str,
        usage_bytes: int,
        created_at: int,
        last_error_message: str | None,
) -> CompanyVectorStoreFileRead:
    return CompanyVectorStoreFileRead(
        id=file_id,
        filename=filename,
        status=status_name,
        usage_bytes=usage_bytes,
        created_at=datetime.fromtimestamp(created_at, tz=timezone.utc),
        last_error_message=last_error_message,
    )


def build_company_vector_store_file_batch_read(batch) -> CompanyVectorStoreFileBatchRead:
    return CompanyVectorStoreFileBatchRead(
        vector_store_id=batch.vector_store_id,
        status=batch.status,
        uploaded_count=batch.file_counts.total,
        completed_count=batch.file_counts.completed,
        failed_count=batch.file_counts.failed,
        cancelled_count=batch.file_counts.cancelled,
        in_progress_count=batch.file_counts.in_progress,
    )


def ensure_company_has_vector_store(company) -> str:
    vector_store_id = (company.vector_store_id or "").strip()
    if not vector_store_id:
        raise conflict_exception("Vector store is not configured for this company yet.")
    return vector_store_id


def raise_vector_store_http_error(error: Exception) -> None:
    if isinstance(error, RuntimeError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    if isinstance(error, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if isinstance(error, OpenAIError):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    raise error


__all__ = [
    "build_company_beeline_integration_read",
    "build_company_vector_store_read",
    "build_company_vector_store_file_read",
    "build_company_vector_store_file_batch_read",
    "ensure_company_has_vector_store",
    "raise_vector_store_http_error",
]
