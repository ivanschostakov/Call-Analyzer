from types import SimpleNamespace

import pytest

from src.app.modules.transcriptions.schemas import TranscriptionEmployeeAssignment


@pytest.mark.asyncio
async def test_assign_transcription_employee_overrides_ai_result(monkeypatch) -> None:
    from src.app.modules.transcriptions import router

    transcription = SimpleNamespace(id=41, detected_employee_user_id=7)
    refreshed = SimpleNamespace(id=41)
    current_user = SimpleNamespace(id=2)
    seen: dict[str, object] = {}

    async def fake_get_accessible(*args):
        return transcription, True

    async def fake_get_company(*args):
        return SimpleNamespace(id=1, owner_id=2)

    async def fake_get_membership(db, company_id, user_id):
        assert company_id == 1
        assert user_id == 4
        return SimpleNamespace(user_id=4)

    async def fake_update(db, current, payload):
        seen["employee_user_id"] = payload.detected_employee_user_id
        return current

    async def fake_reload(db, transcription_id):
        assert transcription_id == 41
        return refreshed

    async def fake_is_favorite(*args):
        return False

    monkeypatch.setattr(router, "get_accessible_transcription_by_file_or_404", fake_get_accessible)
    monkeypatch.setattr(router, "get_accessible_company_or_404", fake_get_company)
    monkeypatch.setattr(router, "get_employee_by_company_id_and_user_id", fake_get_membership)
    monkeypatch.setattr(router, "update_transcription", fake_update)
    monkeypatch.setattr(router, "get_transcription_by_id", fake_reload)
    monkeypatch.setattr(router, "is_transcription_favorite", fake_is_favorite)
    monkeypatch.setattr(router, "build_transcription_response", lambda item, **kwargs: item)

    result = await router.assign_transcription_employee(
        company_id=1,
        file_id="beeline_41",
        payload=TranscriptionEmployeeAssignment(employee_user_id=4),
        current_user=current_user,
        db=object(),
    )

    assert result is refreshed
    assert seen["employee_user_id"] == 4


@pytest.mark.asyncio
async def test_assign_transcription_employee_can_reset_to_unresolved(monkeypatch) -> None:
    from src.app.modules.transcriptions import router

    transcription = SimpleNamespace(id=42, detected_employee_user_id=4)
    current_user = SimpleNamespace(id=2)
    seen: dict[str, object] = {}

    async def fake_get_accessible(*args):
        return transcription, True

    async def fake_update(db, current, payload):
        seen["employee_user_id"] = payload.detected_employee_user_id
        return current

    async def fake_reload(*args):
        return transcription

    async def fake_is_favorite(*args):
        return False

    monkeypatch.setattr(router, "get_accessible_transcription_by_file_or_404", fake_get_accessible)
    monkeypatch.setattr(router, "update_transcription", fake_update)
    monkeypatch.setattr(router, "get_transcription_by_id", fake_reload)
    monkeypatch.setattr(router, "is_transcription_favorite", fake_is_favorite)
    monkeypatch.setattr(router, "build_transcription_response", lambda item, **kwargs: item)

    await router.assign_transcription_employee(
        company_id=1,
        file_id="beeline_42",
        payload=TranscriptionEmployeeAssignment(employee_user_id=None),
        current_user=current_user,
        db=object(),
    )

    assert seen["employee_user_id"] is None
