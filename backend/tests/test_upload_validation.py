import io

from starlette.datastructures import Headers, UploadFile

from src.app.modules.uploads.helpers import is_supported_audio_upload


def build_upload(filename: str, content_type: str | None) -> UploadFile:
    headers = Headers({"content-type": content_type}) if content_type is not None else Headers()
    return UploadFile(io.BytesIO(b"audio"), filename=filename, headers=headers)


def test_is_supported_audio_upload_accepts_audio_content_type() -> None:
    upload = build_upload("clip.bin", "audio/wav")

    assert is_supported_audio_upload(upload) is True


def test_is_supported_audio_upload_accepts_octet_stream_with_audio_extension() -> None:
    upload = build_upload("call.mp3", "application/octet-stream")

    assert is_supported_audio_upload(upload) is True


def test_is_supported_audio_upload_accepts_empty_content_type_with_audio_extension() -> None:
    upload = build_upload("call.wav", None)

    assert is_supported_audio_upload(upload) is True


def test_is_supported_audio_upload_accepts_mp4_audio_filename_with_video_content_type() -> None:
    upload = build_upload("call.m4a", "video/mp4")

    assert is_supported_audio_upload(upload) is True


def test_is_supported_audio_upload_rejects_non_audio_file() -> None:
    upload = build_upload("notes.txt", "text/plain")

    assert is_supported_audio_upload(upload) is False
