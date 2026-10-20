from datetime import timezone


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def analysis_is_stale(analysis, transcription) -> bool:
    if transcription is None:
        return False
    if getattr(transcription, "status", "completed") != "completed":
        return True
    transcribed_at = getattr(transcription, "transcribed_at", None)
    created_at = getattr(analysis, "created_at", None)
    return bool(transcribed_at and created_at and _utc(transcribed_at) > _utc(created_at))


def transcription_matches_snapshot(transcription, text, transcribed_at) -> bool:
    return (
        transcription.status == "completed"
        and transcription.text == text
        and getattr(transcription, "transcribed_at", None) == transcribed_at
    )
