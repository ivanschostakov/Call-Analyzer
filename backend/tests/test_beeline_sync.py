from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest


def build_company(*, company_id: int, owner_id: int):
    timestamp = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=company_id,
        owner_id=owner_id,
        beeline_api_token="saved-token",
        beeline_auto_export_enabled=True,
        beeline_last_sync_target_date=None,
        beeline_last_sync_started_at=timestamp,
        beeline_last_sync_finished_at=None,
        beeline_last_sync_status=None,
        beeline_last_sync_error=None,
        beeline_last_auto_sync_target_date=None,
        beeline_last_auto_sync_started_at=timestamp,
        beeline_last_auto_sync_finished_at=None,
        beeline_last_auto_sync_status=None,
        beeline_last_auto_sync_error=None,
    )


class FakeSessionManager:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_sync_company_beeline_recordings_uses_requested_target_date(monkeypatch) -> None:
    from src.app.services import beeline_sync

    requested_date = date(2026, 3, 30)
    company = build_company(company_id=11, owner_id=42)
    seen: dict[str, object] = {}
    update_payloads: list[dict[str, object]] = []

    def fake_get_session():
        return FakeSessionManager()

    async def fake_get_company_by_id(db, company_id):
        assert company_id == company.id
        return company

    async def fake_update_company(db, current_company, payload):
        values = payload.model_dump(exclude_unset=True)
        update_payloads.append(values)
        for field, value in values.items():
            setattr(current_company, field, value)
        return current_company

    class FakeBeelineClient:
        def __init__(self, *args, **kwargs):
            seen["client_settings"] = kwargs.get("settings")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_sync_company_records(*, client, company_id, owner_id, target_date):
        seen["sync_company_id"] = company_id
        seen["sync_owner_id"] = owner_id
        seen["sync_target_date"] = target_date
        return 3

    monkeypatch.setattr(beeline_sync, "get_session", fake_get_session)
    monkeypatch.setattr(beeline_sync, "get_company_by_id", fake_get_company_by_id)
    monkeypatch.setattr(beeline_sync, "update_company", fake_update_company)
    monkeypatch.setattr(beeline_sync, "BeelineClient", FakeBeelineClient)
    monkeypatch.setattr(beeline_sync, "_sync_company_records", fake_sync_company_records)

    imported_count = await beeline_sync.sync_company_beeline_recordings(company.id, requested_date)

    assert imported_count == 3
    assert seen["sync_company_id"] == company.id
    assert seen["sync_owner_id"] == company.owner_id
    assert seen["sync_target_date"] == requested_date
    assert update_payloads[0]["beeline_last_sync_target_date"] == requested_date
    assert update_payloads[-1]["beeline_last_sync_target_date"] == requested_date


@pytest.mark.asyncio
async def test_run_due_beeline_syncs_uses_current_ufa_date_without_subtracting_day(monkeypatch) -> None:
    from src.app.services import beeline_sync

    current_ufa_day = date(2026, 4, 1)
    current_ufa_datetime = datetime(2026, 4, 1, 10, 0, tzinfo=beeline_sync.UFA_TZ)
    company = build_company(company_id=11, owner_id=42)
    company.beeline_last_auto_sync_target_date = None
    seen_targets: list[date] = []

    class FakeSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def fake_get_session():
        return FakeSession()

    async def fake_list_companies_with_beeline_auto_export_enabled(db):
        return [company]

    async def fake_sync_company_beeline_recordings(company_id, target_date, *, sync_kind=beeline_sync.BEELINE_SYNC_KIND_MANUAL):
        seen_targets.append(target_date)
        assert sync_kind == beeline_sync.BEELINE_SYNC_KIND_AUTO
        return 0

    monkeypatch.setattr(beeline_sync, "ufa_now", lambda: current_ufa_datetime)
    monkeypatch.setattr(beeline_sync, "get_session", fake_get_session)
    monkeypatch.setattr(beeline_sync, "list_companies_with_beeline_auto_export_enabled", fake_list_companies_with_beeline_auto_export_enabled)
    monkeypatch.setattr(beeline_sync, "sync_company_beeline_recordings", fake_sync_company_beeline_recordings)

    synced_count = await beeline_sync.run_due_beeline_syncs()

    assert synced_count == 1
    assert seen_targets == [current_ufa_day]


def test_company_sync_due_uses_auto_sync_fields_not_manual_sync_fields() -> None:
    from src.app.services import beeline_sync

    target_date = date(2026, 4, 1)
    company = build_company(company_id=11, owner_id=42)
    company.beeline_last_sync_target_date = target_date
    company.beeline_last_sync_status = beeline_sync.BEELINE_SYNC_STATUS_SUCCESS
    company.beeline_last_auto_sync_target_date = None
    company.beeline_last_auto_sync_status = None

    assert beeline_sync._company_sync_due(company, target_date) is True


def test_company_sync_due_repeats_when_two_hour_window_changes() -> None:
    from src.app.services import beeline_sync

    company = build_company(company_id=11, owner_id=42)
    company.beeline_last_auto_sync_target_date = date(2026, 4, 1)
    company.beeline_last_auto_sync_started_at = datetime(2026, 4, 1, 10, 15, tzinfo=beeline_sync.UFA_TZ)
    company.beeline_last_auto_sync_status = beeline_sync.BEELINE_SYNC_STATUS_SUCCESS

    assert beeline_sync._company_sync_due(company, datetime(2026, 4, 1, 11, 59, tzinfo=beeline_sync.UFA_TZ)) is False
    assert beeline_sync._company_sync_due(company, datetime(2026, 4, 1, 12, 0, tzinfo=beeline_sync.UFA_TZ)) is True


def test_next_sync_check_uses_two_hour_boundaries() -> None:
    from src.app.services import beeline_sync

    assert beeline_sync._next_sync_check(datetime(2026, 4, 1, 10, 15, tzinfo=beeline_sync.UFA_TZ)) == datetime(2026, 4, 1, 12, 0, tzinfo=beeline_sync.UFA_TZ)
    assert beeline_sync._next_sync_check(datetime(2026, 4, 1, 23, 30, tzinfo=beeline_sync.UFA_TZ)) == datetime(2026, 4, 2, 0, 0, tzinfo=beeline_sync.UFA_TZ)


@pytest.mark.asyncio
async def test_import_record_if_missing_skips_short_recordings(monkeypatch) -> None:
    from src.app.services import beeline_sync
    from src.integrations.beeline.models import BeelineCallRecord

    class FakeSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def fake_get_session():
        return FakeSession()

    download_called = {"value": False}

    class FakeClient:
        async def download_record_file(self, record_id):
            download_called["value"] = True
            raise AssertionError("download should not be called for short recordings")

    monkeypatch.setattr(beeline_sync, "get_session", fake_get_session)

    result = await beeline_sync._import_record_if_missing(
        client=FakeClient(),
        company_id=11,
        owner_id=42,
        target_date=date(2026, 3, 30),
        record=BeelineCallRecord(
            record_id="482024410",
            ext_tracking_id="ext-1",
            user_id="user-1",
            duration_seconds=119,
        ),
    )

    assert result is False
    assert download_called["value"] is False


@pytest.mark.asyncio
async def test_import_record_if_missing_persists_call_started_at(monkeypatch, tmp_path) -> None:
    from src.app.services import beeline_sync
    from src.integrations.beeline.models import BeelineCallRecord

    class FakeSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def fake_get_session():
        return FakeSession()

    seen: dict[str, object] = {}

    class FakeClient:
        async def download_record_file(self, record_id):
            assert record_id == "482024410"
            return SimpleNamespace(content=b"audio-data", content_type="audio/mpeg", filename="call.mp3")

    async def fake_get_transcription_by_company_id_and_file_id(db, company_id, file_id):
        return None

    async def fake_create_transcription(db, payload):
        seen["call_started_at"] = payload.call_started_at
        return SimpleNamespace(id=501)

    async def fake_enqueue_transcription_job(transcription_id):
        seen["queued_transcription_id"] = transcription_id
        return True

    monkeypatch.setattr(beeline_sync, "get_session", fake_get_session)
    monkeypatch.setattr(beeline_sync, "COMPANIES_UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(beeline_sync, "get_transcription_by_company_id_and_file_id", fake_get_transcription_by_company_id_and_file_id)
    monkeypatch.setattr(beeline_sync, "create_transcription", fake_create_transcription)
    monkeypatch.setattr(beeline_sync, "enqueue_transcription_job", fake_enqueue_transcription_job)

    call_started_at = datetime(2026, 3, 30, 15, 45, tzinfo=timezone.utc)
    result = await beeline_sync._import_record_if_missing(
        client=FakeClient(),
        company_id=11,
        owner_id=42,
        target_date=date(2026, 3, 30),
        record=BeelineCallRecord(
            record_id="482024410",
            ext_tracking_id="ext-1",
            user_id="user-1",
            duration_seconds=180,
            started_at=call_started_at,
        ),
    )

    assert result is True
    assert seen["call_started_at"] == call_started_at
    assert seen["queued_transcription_id"] == 501
