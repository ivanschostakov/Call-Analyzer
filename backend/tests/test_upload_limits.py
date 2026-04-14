import io

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile


@pytest.mark.asyncio
async def test_save_upload_file_rejects_oversized_upload(tmp_path) -> None:
    from src.app.modules.uploads.helpers import save_upload_file

    destination = tmp_path / "clip.wav"
    upload = UploadFile(
        io.BytesIO(b"abcdef"),
        filename="clip.wav",
        headers=Headers({"content-type": "audio/wav"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await save_upload_file(upload, destination, max_bytes=4)

    await upload.close()

    assert exc_info.value.status_code == 413
    assert "4 byte limit" in exc_info.value.detail
    assert not destination.exists() or destination.stat().st_size == 0
