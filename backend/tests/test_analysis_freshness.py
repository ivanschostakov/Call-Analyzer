from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.analyzer.freshness import analysis_is_stale, transcription_matches_snapshot


def test_retranscription_invalidates_old_analysis_not_assignment_changes():
    now = datetime.now(timezone.utc)
    analysis = SimpleNamespace(created_at=now)
    transcription = SimpleNamespace(status="completed", text="Hello", transcribed_at=now - timedelta(hours=1), updated_at=now + timedelta(hours=2))
    assert not analysis_is_stale(analysis, transcription)
    transcription.transcribed_at = now + timedelta(hours=3)
    assert analysis_is_stale(analysis, transcription)
    transcription.status = "queued"
    transcription.transcribed_at = None
    assert analysis_is_stale(analysis, transcription)


def test_snapshot_rejects_changed_text_version_and_status():
    now = datetime.now(timezone.utc)
    transcription = SimpleNamespace(status="completed", text="Hello", transcribed_at=now)
    assert transcription_matches_snapshot(transcription, "Hello", now)
    assert not transcription_matches_snapshot(transcription, "Old", now)
    assert not transcription_matches_snapshot(transcription, "Hello", now - timedelta(seconds=1))
    transcription.status = "processing"
    assert not transcription_matches_snapshot(transcription, "Hello", now)
