from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


def build_transcription(
    transcription_id: int,
    source_path: Path,
    wav_path: Path,
):
    return SimpleNamespace(
        id=transcription_id,
        source_path=str(source_path),
        file_path=str(wav_path),
        created_at=datetime.now(timezone.utc),
    )


def test_remove_generated_wav_keeps_source(tmp_path) -> None:
    from src.app.services.audio_cleanup import remove_generated_wav

    source_path = tmp_path / "call.mp3"
    wav_path = tmp_path / "call.wav"
    source_path.write_bytes(b"source")
    wav_path.write_bytes(b"generated-wav")

    deleted, bytes_freed = remove_generated_wav(
        build_transcription(1, source_path, wav_path)
    )

    assert deleted is True
    assert bytes_freed == len(b"generated-wav")
    assert source_path.exists()
    assert not wav_path.exists()


@pytest.mark.asyncio
async def test_cleanup_deletes_expired_audio_and_keeps_recent_source(
    monkeypatch,
    tmp_path,
) -> None:
    from src.app.services import audio_cleanup

    recent_source = tmp_path / "recent.mp3"
    recent_wav = tmp_path / "recent.wav"
    expired_source = tmp_path / "expired.mp3"
    expired_wav = tmp_path / "expired.wav"
    for path in (recent_source, recent_wav, expired_source, expired_wav):
        path.write_bytes(path.name.encode())

    recent = build_transcription(1, recent_source, recent_wav)
    expired = build_transcription(2, expired_source, expired_wav)

    @asynccontextmanager
    async def fake_session():
        yield object()

    async def fake_list_completed(db):
        return [recent, expired]

    async def fake_list_expired(db, older_than):
        return [expired]

    monkeypatch.setattr(audio_cleanup, "get_session", fake_session)
    monkeypatch.setattr(
        audio_cleanup,
        "list_completed_transcriptions_for_wav_cleanup",
        fake_list_completed,
    )
    monkeypatch.setattr(
        audio_cleanup,
        "list_expired_unfavorited_transcriptions",
        fake_list_expired,
    )

    result = await audio_cleanup.run_audio_cleanup_once()

    assert result.wav_files_deleted == 1
    assert result.expired_files_deleted == 2
    assert recent_source.exists()
    assert not recent_wav.exists()
    assert not expired_source.exists()
    assert not expired_wav.exists()
