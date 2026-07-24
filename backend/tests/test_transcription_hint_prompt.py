from src.app.services.transcription_jobs import build_transcription_hint_prompt


def test_build_transcription_hint_prompt_includes_clean_unique_employee_names() -> None:
    result = build_transcription_hint_prompt(
        "Компания ElixirPeptide.",
        [" Елена Забродина ", "Алия Ялалова", "Елена Забродина", None],
    )

    assert result == (
        "Компания ElixirPeptide. "
        "Имена сотрудников для точного распознавания: Алия Ялалова, Елена Забродина."
    )


def test_build_transcription_hint_prompt_returns_none_without_content() -> None:
    assert build_transcription_hint_prompt(None, [None, "  "]) is None
