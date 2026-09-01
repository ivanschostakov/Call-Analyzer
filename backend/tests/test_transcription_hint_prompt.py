from src.app.services.transcription_jobs import build_transcription_hint_prompt, is_likely_transcription_prompt_echo


def test_build_transcription_hint_prompt_includes_clean_unique_employee_names() -> None:
    result = build_transcription_hint_prompt(
        "Компания ElixirPeptide.",
        [" Елена Забродина ", "Алия Ялалова", "Елена Забродина", None],
    )

    assert result == (
        "Справочный словарь для распознавания. Не добавляй эти слова в транскрипцию, "
        "если они не произнесены в аудио. Термины компании: Компания ElixirPeptide; "
        "Имена сотрудников: Алия Ялалова, Елена Забродина."
    )


def test_build_transcription_hint_prompt_returns_none_without_content() -> None:
    assert build_transcription_hint_prompt(None, [None, "  "]) is None


def test_prompt_echo_detection_catches_full_and_partial_echoes() -> None:
    prompt = "Наша компания называется ElixirPeptide. Имена сотрудников: Анна Нефедова, Елена Забродина."

    assert is_likely_transcription_prompt_echo(prompt, prompt)
    assert is_likely_transcription_prompt_echo("Наша компания называется ElixirPeptide", prompt)


def test_prompt_echo_detection_keeps_real_conversation() -> None:
    prompt = "Наша компания называется ElixirPeptide. Имена сотрудников: Анна Нефедова."
    transcript = "Здравствуйте. Я вчера оплатил заказ, но пока не получил трек-номер. Проверьте, пожалуйста."

    assert not is_likely_transcription_prompt_echo(transcript, prompt)
