from datetime import datetime, timezone
import logging

from openai import OpenAIError
from openai.types.vector_store import VectorStore
from openai.types.vector_stores.vector_store_file import VectorStoreFile
from openai.types.vector_stores.vector_store_file_batch import VectorStoreFileBatch

from config import OPENAI_API_KEY
from src.app.openai_client import build_openai_async_client
from src.app.observability import log_exception, log_info, log_warning, start_timer

logger = logging.getLogger(__name__)


def _to_datetime(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


class VectorStoreService:
    def __init__(self, openai_api_key: str | None = OPENAI_API_KEY):
        self._client = build_openai_async_client(openai_api_key)

    def _get_client(self):
        if self._client is None:
            raise RuntimeError("OpenAI is not configured. Set OPENAI_API_KEY.")
        return self._client

    async def create_vector_store(self, *, name: str, metadata: dict[str, str] | None = None) -> VectorStore:
        client = self._get_client()
        timer = start_timer()
        log_info(logger, "vector_store.create.start", name=name, metadata=metadata)
        try:
            vector_store = await client.vector_stores.create(
                name=name,
                metadata=metadata or None,
            )
        except Exception:
            log_exception(logger, "vector_store.create.failed", name=name, metadata=metadata)
            raise
        log_info(logger, "vector_store.create.success", vector_store_id=vector_store.id, duration_ms=timer.elapsed_ms)
        return vector_store

    async def upload_files(self, *, vector_store_id: str, files: list[tuple[str, bytes, str]]) -> VectorStoreFileBatch:
        client = self._get_client()
        timer = start_timer()
        log_info(
            logger,
            "vector_store.upload.start",
            vector_store_id=vector_store_id,
            file_count=len(files),
            filenames=[name for name, _, _ in files],
            total_bytes=sum(len(contents) for _, contents, _ in files),
        )
        try:
            batch = await client.vector_stores.file_batches.upload_and_poll(
                vector_store_id,
                files=files,
            )
        except Exception:
            log_exception(logger, "vector_store.upload.failed", vector_store_id=vector_store_id, file_count=len(files))
            raise
        log_info(
            logger,
            "vector_store.upload.success",
            vector_store_id=vector_store_id,
            duration_ms=timer.elapsed_ms,
            status=batch.status,
            total=batch.file_counts.total,
            completed=batch.file_counts.completed,
            failed=batch.file_counts.failed,
        )
        return batch

    async def list_vector_store_files(self, *, vector_store_id: str, limit: int = 100) -> list[VectorStoreFile]:
        client = self._get_client()
        timer = start_timer()
        log_info(logger, "vector_store.files.list.start", vector_store_id=vector_store_id, limit=limit)
        paginator = client.vector_stores.files.list(
            vector_store_id=vector_store_id,
            limit=limit,
            order="desc",
        )
        items = [item async for item in paginator]
        log_info(logger, "vector_store.files.list.success", vector_store_id=vector_store_id, count=len(items), duration_ms=timer.elapsed_ms)
        return items

    async def resolve_filename(self, file_id: str) -> str | None:
        client = self._get_client()
        timer = start_timer()
        log_info(logger, "vector_store.file.resolve.start", file_id=file_id)
        try:
            file_object = await client.files.retrieve(file_id)
        except OpenAIError:
            log_warning(logger, "vector_store.file.resolve.failed", file_id=file_id, duration_ms=timer.elapsed_ms)
            return None
        log_info(logger, "vector_store.file.resolve.success", file_id=file_id, filename=file_object.filename, duration_ms=timer.elapsed_ms)
        return file_object.filename

    async def delete_vector_store(self, *, vector_store_id: str) -> None:
        client = self._get_client()
        timer = start_timer()
        log_info(logger, "vector_store.delete.start", vector_store_id=vector_store_id)
        try:
            await client.vector_stores.delete(vector_store_id)
        except Exception:
            log_exception(logger, "vector_store.delete.failed", vector_store_id=vector_store_id)
            raise
        log_info(logger, "vector_store.delete.success", vector_store_id=vector_store_id, duration_ms=timer.elapsed_ms)


vector_store_service = VectorStoreService()

__all__ = ["VectorStoreService", "vector_store_service", "_to_datetime"]
