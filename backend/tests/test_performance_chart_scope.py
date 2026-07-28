from types import SimpleNamespace

from src.app.modules.analysis.router import resolve_performance_chart_scope
from src.enums import UserRole


def test_employee_chart_uses_own_calls_and_company_template() -> None:
    user = SimpleNamespace(id=17, role=UserRole.EMPLOYEE)
    company = SimpleNamespace(beeline_auto_analysis_template_id=41)

    template_id, employee_user_id = resolve_performance_chart_scope(
        current_user=user,
        company=company,
        requested_template_id=99,
        requested_employee_user_id=23,
    )

    assert template_id == 41
    assert employee_user_id == 17


def test_supervisor_chart_keeps_selected_employee_and_company_template() -> None:
    user = SimpleNamespace(id=5, role=UserRole.ADMIN)
    company = SimpleNamespace(beeline_auto_analysis_template_id=41)

    template_id, employee_user_id = resolve_performance_chart_scope(
        current_user=user,
        company=company,
        requested_template_id=99,
        requested_employee_user_id=17,
    )

    assert template_id == 41
    assert employee_user_id == 17


def test_chart_falls_back_to_requested_template_without_company_setting() -> None:
    user = SimpleNamespace(id=5, role=UserRole.OWNER)
    company = SimpleNamespace(beeline_auto_analysis_template_id=None)

    template_id, employee_user_id = resolve_performance_chart_scope(
        current_user=user,
        company=company,
        requested_template_id=99,
        requested_employee_user_id=None,
    )

    assert template_id == 99
    assert employee_user_id is None
