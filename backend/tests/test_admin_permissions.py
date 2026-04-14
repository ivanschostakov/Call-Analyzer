from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from config import ufa_now
from src.app.modules.companies.schemas import CompanyBeelineIntegrationSyncRangePayload, CompanyBeelineIntegrationUpdatePayload
from src.app.modules.common import can_manage_company, ensure_can_create_company, get_visible_user_ids_for_company
from src.enums import UserRole


def build_user(*, user_id: int, role: UserRole):
    return SimpleNamespace(id=user_id, role=role)


def build_company(*, company_id: int, owner_id: int):
    timestamp = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=company_id,
        owner_id=owner_id,
        name=f"Company {company_id}",
        description=None,
        vector_store_id=None,
        beeline_api_token=None,
        beeline_auto_export_enabled=False,
        beeline_auto_analysis_template_id=None,
        beeline_last_sync_target_date=None,
        beeline_last_sync_started_at=None,
        beeline_last_sync_finished_at=None,
        beeline_last_sync_status=None,
        beeline_last_sync_error=None,
        beeline_last_auto_sync_target_date=None,
        beeline_last_auto_sync_started_at=None,
        beeline_last_auto_sync_finished_at=None,
        beeline_last_auto_sync_status=None,
        beeline_last_auto_sync_error=None,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_admin_can_manage_any_company() -> None:
    admin = build_user(user_id=7, role=UserRole.ADMIN)
    company = build_company(company_id=11, owner_id=42)

    assert can_manage_company(admin, company) is True


@pytest.mark.asyncio
async def test_admin_can_create_company() -> None:
    admin = build_user(user_id=7, role=UserRole.ADMIN)

    await ensure_can_create_company(admin)


@pytest.mark.asyncio
async def test_admin_sees_all_company_users() -> None:
    admin = build_user(user_id=7, role=UserRole.ADMIN)
    company = build_company(company_id=11, owner_id=42)

    visible_user_ids = await get_visible_user_ids_for_company(None, admin, company)

    assert visible_user_ids is None


@pytest.mark.asyncio
async def test_list_companies_route_returns_all_companies_for_admin(monkeypatch) -> None:
    from src.app.modules.companies import router as companies_router

    companies = [
        build_company(company_id=1, owner_id=101),
        build_company(company_id=2, owner_id=202),
    ]
    calls = {"all": 0, "accessible": 0}

    async def fake_list_companies(db):
        calls["all"] += 1
        return companies

    async def fake_list_companies_accessible_to_user_id(db, user_id):
        calls["accessible"] += 1
        return []

    monkeypatch.setattr(companies_router, "list_companies", fake_list_companies)
    monkeypatch.setattr(companies_router, "list_companies_accessible_to_user_id", fake_list_companies_accessible_to_user_id)

    response = await companies_router.list_companies_route(
        current_user=build_user(user_id=7, role=UserRole.ADMIN),
        db=None,
    )

    assert [item.id for item in response] == [1, 2]
    assert calls == {"all": 1, "accessible": 0}


@pytest.mark.asyncio
async def test_admin_can_set_company_beeline_integration(monkeypatch) -> None:
    from src.app.modules.companies import router as companies_router
    from src.app.services import beeline_sync

    admin = build_user(user_id=7, role=UserRole.ADMIN)
    company = build_company(company_id=11, owner_id=42)
    template = SimpleNamespace(id=501, company_id=company.id)
    sync_calls: list[tuple[int, object]] = []

    async def fake_get_manageable_company_or_404(db, current_user, company_id):
        assert current_user.id == admin.id
        assert company_id == company.id
        return company

    async def fake_get_default_template_by_company_id(db, company_id):
        assert company_id == company.id
        return template

    async def fake_get_template_by_id(db, template_id):
        assert template_id == template.id
        return template

    async def fake_update_company(db, current_company, payload):
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(current_company, field, value)
        return current_company

    async def fake_sync_company_beeline_recordings(company_id, target_date):
        sync_calls.append((company_id, target_date))
        company.beeline_last_sync_target_date = target_date
        company.beeline_last_sync_status = "success"
        return 0

    monkeypatch.setattr(companies_router, "get_manageable_company_or_404", fake_get_manageable_company_or_404)
    monkeypatch.setattr(companies_router, "get_default_template_by_company_id", fake_get_default_template_by_company_id)
    monkeypatch.setattr(companies_router, "get_template_by_id", fake_get_template_by_id)
    monkeypatch.setattr(companies_router, "update_company", fake_update_company)
    monkeypatch.setattr(beeline_sync, "sync_company_beeline_recordings", fake_sync_company_beeline_recordings)

    response = await companies_router.set_company_beeline_integration_route(
        company_id=company.id,
        payload=CompanyBeelineIntegrationUpdatePayload(api_token="token-123"),
        current_user=admin,
        db=None,
    )

    assert response.company_id == company.id
    assert response.enabled is True
    assert response.has_token is True
    assert response.analysis_template_id == template.id
    assert sync_calls == [(company.id, ufa_now().date())]


@pytest.mark.asyncio
async def test_admin_can_run_beeline_current_date_sync(monkeypatch) -> None:
    from src.app.modules.companies import router as companies_router
    from src.app.services import beeline_sync

    admin = build_user(user_id=7, role=UserRole.ADMIN)
    company = build_company(company_id=11, owner_id=42)
    company.beeline_api_token = "saved-token"
    company.beeline_auto_export_enabled = True
    sync_calls: list[tuple[int, object]] = []

    async def fake_get_manageable_company_or_404(db, current_user, company_id):
        assert current_user.id == admin.id
        assert company_id == company.id
        return company

    async def fake_sync_company_beeline_recordings(company_id, target_date):
        sync_calls.append((company_id, target_date))
        company.beeline_last_sync_target_date = target_date
        company.beeline_last_sync_status = "success"
        return 0

    monkeypatch.setattr(companies_router, "get_manageable_company_or_404", fake_get_manageable_company_or_404)
    monkeypatch.setattr(beeline_sync, "sync_company_beeline_recordings", fake_sync_company_beeline_recordings)

    response = await companies_router.sync_company_beeline_current_date_route(
        company_id=company.id,
        current_user=admin,
        db=None,
    )

    assert response.company_id == company.id
    assert response.enabled is True
    assert response.last_sync_status == "success"
    assert sync_calls == [(company.id, ufa_now().date())]


@pytest.mark.asyncio
async def test_admin_can_run_beeline_date_range_sync(monkeypatch) -> None:
    from src.app.modules.companies import router as companies_router
    from src.app.services import beeline_sync

    admin = build_user(user_id=7, role=UserRole.ADMIN)
    company = build_company(company_id=11, owner_id=42)
    company.beeline_api_token = "saved-token"
    company.beeline_auto_export_enabled = True
    sync_calls: list[tuple[int, object, object]] = []

    async def fake_get_manageable_company_or_404(db, current_user, company_id):
        assert current_user.id == admin.id
        assert company_id == company.id
        return company

    async def fake_sync_company_beeline_recordings_range(company_id, date_from, date_to):
        sync_calls.append((company_id, date_from, date_to))
        company.beeline_last_sync_target_date = date_to
        company.beeline_last_sync_status = "success"
        return 0

    monkeypatch.setattr(companies_router, "get_manageable_company_or_404", fake_get_manageable_company_or_404)
    monkeypatch.setattr(beeline_sync, "sync_company_beeline_recordings_range", fake_sync_company_beeline_recordings_range)

    response = await companies_router.sync_company_beeline_range_route(
        company_id=company.id,
        payload=CompanyBeelineIntegrationSyncRangePayload(
            date_from=datetime(2026, 3, 29, tzinfo=timezone.utc).date(),
            date_to=datetime(2026, 3, 30, tzinfo=timezone.utc).date(),
        ),
        current_user=admin,
        db=None,
    )

    assert response.company_id == company.id
    assert response.enabled is True
    assert response.last_sync_status == "success"
    assert sync_calls == [(company.id, datetime(2026, 3, 29, tzinfo=timezone.utc).date(), datetime(2026, 3, 30, tzinfo=timezone.utc).date())]


@pytest.mark.asyncio
async def test_admin_can_update_company_summary_questions_without_overwriting_unset_fields(monkeypatch) -> None:
    from src.app.modules.companies import router as companies_router
    from src.app.modules.companies.schemas import CompanyUpdatePayload

    admin = build_user(user_id=7, role=UserRole.ADMIN)
    company = build_company(company_id=11, owner_id=42)
    company.report_summary_questions = []
    captured: dict[str, object] = {}

    async def fake_get_manageable_company_or_404(db, current_user, company_id):
        assert current_user.id == admin.id
        assert company_id == company.id
        return company

    async def fake_update_company(db, current_company, payload):
        captured["changes"] = payload.model_dump(exclude_unset=True)
        for field, value in captured["changes"].items():
            setattr(current_company, field, value)
        return current_company

    monkeypatch.setattr(companies_router, "get_manageable_company_or_404", fake_get_manageable_company_or_404)
    monkeypatch.setattr(companies_router, "update_company", fake_update_company)

    response = await companies_router.update_company_route(
        company_id=company.id,
        payload=CompanyUpdatePayload(report_summary_questions=["aa"]),
        current_user=admin,
        db=None,
    )

    assert captured["changes"] == {"report_summary_questions": ["aa"]}
    assert response.name == company.name
    assert response.description == company.description
    assert response.report_summary_questions == ["aa"]
