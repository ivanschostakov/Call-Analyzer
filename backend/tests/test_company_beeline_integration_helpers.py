from datetime import date, datetime
from types import SimpleNamespace

from config import UFA_TZ
from src.app.modules.companies.helpers import build_company_beeline_integration_read


def build_company(**overrides):
    base = dict(
        id=1,
        beeline_api_token="secret-token",
        beeline_auto_export_enabled=True,
        beeline_auto_analysis_template_id=7,
        beeline_last_sync_target_date=date(2026, 4, 14),
        beeline_last_sync_started_at=datetime(2026, 4, 14, 9, 0, tzinfo=UFA_TZ),
        beeline_last_sync_finished_at=datetime(2026, 4, 14, 9, 5, tzinfo=UFA_TZ),
        beeline_last_sync_status="success",
        beeline_last_sync_error=None,
        beeline_last_auto_sync_target_date=date(2026, 4, 14),
        beeline_last_auto_sync_started_at=datetime(2026, 4, 14, 10, 0, tzinfo=UFA_TZ),
        beeline_last_auto_sync_finished_at=datetime(2026, 4, 14, 10, 1, tzinfo=UFA_TZ),
        beeline_last_auto_sync_status="success",
        beeline_last_auto_sync_error=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_company_beeline_integration_read_prefers_newer_auto_sync() -> None:
    company = build_company()

    result = build_company_beeline_integration_read(company)

    assert result.last_sync_started_at == company.beeline_last_auto_sync_started_at
    assert result.last_sync_finished_at == company.beeline_last_auto_sync_finished_at
    assert result.last_sync_target_date == company.beeline_last_auto_sync_target_date
    assert result.last_sync_status == company.beeline_last_auto_sync_status


def test_build_company_beeline_integration_read_falls_back_to_manual_sync() -> None:
    company = build_company(
        beeline_last_auto_sync_started_at=None,
        beeline_last_auto_sync_finished_at=None,
        beeline_last_auto_sync_target_date=None,
        beeline_last_auto_sync_status=None,
        beeline_last_auto_sync_error=None,
    )

    result = build_company_beeline_integration_read(company)

    assert result.last_sync_started_at == company.beeline_last_sync_started_at
    assert result.last_sync_finished_at == company.beeline_last_sync_finished_at
    assert result.last_sync_target_date == company.beeline_last_sync_target_date
    assert result.last_sync_status == company.beeline_last_sync_status


def test_build_company_beeline_integration_read_prefers_running_auto_sync_when_newer() -> None:
    company = build_company(
        beeline_last_auto_sync_finished_at=None,
        beeline_last_auto_sync_started_at=datetime(2026, 4, 14, 12, 0, tzinfo=UFA_TZ),
        beeline_last_auto_sync_status="running",
    )

    result = build_company_beeline_integration_read(company)

    assert result.last_sync_started_at == company.beeline_last_auto_sync_started_at
    assert result.last_sync_finished_at is None
    assert result.last_sync_status == "running"
