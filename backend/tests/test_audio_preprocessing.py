from pathlib import Path

from src.app.modules.uploads.helpers import (
    TRANSCRIPTION_AUDIO_FILTER,
    build_transcription_audio_command,
)


def test_transcription_audio_command_preserves_source_channel_count() -> None:
    command = build_transcription_audio_command(
        Path("source.mp3"),
        Path("prepared.flac"),
        source_sample_rate=8000,
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", "source.mp3"]
    assert command[-1] == "prepared.flac"
    assert "-ac" not in command
    assert "-af" in command
    assert "flac" in command
    assert "aresample" not in command[command.index("-af") + 1]


def test_transcription_audio_command_downsamples_high_resolution_audio() -> None:
    command = build_transcription_audio_command(
        Path("source.wav"),
        Path("prepared.flac"),
        source_sample_rate=48000,
    )

    assert "aresample=16000:resampler=soxr:precision=28" in command[command.index("-af") + 1]


def test_transcription_audio_filter_cleans_and_normalizes_each_channel() -> None:
    assert "highpass=f=80" in TRANSCRIPTION_AUDIO_FILTER
    assert "lowpass=f=3800" in TRANSCRIPTION_AUDIO_FILTER
    assert "afftdn=nr=6" in TRANSCRIPTION_AUDIO_FILTER
    assert "nl=none" in TRANSCRIPTION_AUDIO_FILTER
    assert "dynaudnorm=" in TRANSCRIPTION_AUDIO_FILTER
    assert "n=false" in TRANSCRIPTION_AUDIO_FILTER
