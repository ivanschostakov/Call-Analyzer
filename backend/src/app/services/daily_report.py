import asyncio
import logging

from contextlib import suppress
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta

from config import UFA_TZ, ufa_now
from src.app.observability import log_debug, log_exception, log_info, log_warning
from src.database import get_session
from src.database.crud import (
    get_company_by_id,
    get_user_by_id,
    list_analyses_for_daily_report,
    list_companies,
    list_employees_by_company_id,
)
from src.database.models import Analysis, AnalysisResult
from src.enums import CriterionAnswerType, UserRole

from .email import send_daily_report_email

logger = logging.getLogger(__name__)

DAILY_REPORT_HOUR = 21  # 9 PM


@dataclass
class DailyReportCallItem:
    analysis_id: int
    call_name: str
    employee_name: str
    score: float
    template_name: str
    call_date: str | None


@dataclass
class DailyReportData:
    report_date: str
    average_score: float
    total_calls: int
    best_calls: list[DailyReportCallItem]
    worst_calls: list[DailyReportCallItem]


def _deterministic_score(result: AnalysisResult) -> int | None:
    if result.answer_type == CriterionAnswerType.PERCENTAGE:
        v = result.answer_number
        return int(v) if isinstance(v, int) and not isinstance(v, bool) else None
    if result.answer_type == CriterionAnswerType.BOOLEAN:
        v = result.answer_bool
        return 100 if v is True else (0 if v is False else None)
    return None


def _compute_analysis_score(analysis: Analysis) -> float | None:
    scores = []
    for result in analysis.results:
        score = result.score
        if score is None:
            score = _deterministic_score(result)
        if score is not None:
            scores.append(float(score))
    if not scores:
        return None
    return sum(scores) / len(scores)


def _employee_name(analysis: Analysis) -> str:
    t = analysis.transcription
    if t is None:
        user = analysis.created_by
    else:
        user = t.detected_employee_user or t.uploaded_by
    if user is None:
        return "Неизвестный"
    parts = [user.name, user.surname]
    return " ".join(p for p in parts if p).strip() or user.email


def _call_date_str(analysis: Analysis) -> str | None:
    t = analysis.transcription
    dt = (t.call_started_at if t else None) or analysis.created_at
    if dt is None:
        return None
    return dt.strftime("%d.%m.%Y")


def compute_daily_report(analyses: list[Analysis], target_date: date) -> DailyReportData | None:
    scored = []
    for analysis in analyses:
        score = _compute_analysis_score(analysis)
        if score is None:
            continue
        scored.append((analysis, score))

    if not scored:
        return None

    average = sum(s for _, s in scored) / len(scored)
    date_str = target_date.strftime("%d.%m.%Y")

    best_calls = []
    worst_calls = []
    for analysis, score in sorted(scored, key=lambda x: x[1], reverse=True):
        item = DailyReportCallItem(
            analysis_id=analysis.id,
            call_name=analysis.transcription.original_filename if analysis.transcription else f"Анализ #{analysis.id}",
            employee_name=_employee_name(analysis),
            score=round(score, 1),
            template_name=analysis.template_name,
            call_date=_call_date_str(analysis),
        )
        if score >= average:
            best_calls.append(item)
        else:
            worst_calls.append(item)

    return DailyReportData(
        report_date=date_str,
        average_score=round(average, 1),
        total_calls=len(scored),
        best_calls=best_calls,
        worst_calls=worst_calls,
    )


async def send_daily_report_for_company(company_id: int, target_date: date) -> bool:
    async with get_session() as db:
        company = await get_company_by_id(db, company_id)
        if company is None:
            log_warning(logger, "daily_report.company.missing", company_id=company_id)
            return False

        analyses = await list_analyses_for_daily_report(db, company_id, target_date)
        report = compute_daily_report(analyses, target_date)

        if report is None:
            log_info(logger, "daily_report.company.no_data", company_id=company_id, target_date=target_date.isoformat())
            return False

        employees = await list_employees_by_company_id(db, company_id)
        recipients: set[str] = set()

        owner_user = await get_user_by_id(db, company.owner_id)
        if owner_user and owner_user.email:
            recipients.add(owner_user.email)

        for emp in employees:
            if emp.user and emp.user.role == UserRole.ADMIN and emp.user.email:
                recipients.add(emp.user.email)

        company_name = company.name

    if not recipients:
        log_warning(logger, "daily_report.company.no_recipients", company_id=company_id)
        return False

    best = [asdict(c) for c in report.best_calls]
    worst = [asdict(c) for c in report.worst_calls]

    for email in recipients:
        try:
            await send_daily_report_email(
                recipient_email=email,
                company_name=company_name,
                company_id=company_id,
                report_date=report.report_date,
                average_score=report.average_score,
                total_calls=report.total_calls,
                best_calls=best,
                worst_calls=worst,
            )
        except Exception:
            log_exception(logger, "daily_report.email.failed", company_id=company_id, recipient=email)

    log_info(logger, "daily_report.company.sent", company_id=company_id, target_date=target_date.isoformat(), recipient_count=len(recipients))
    return True


async def send_all_daily_reports(target_date: date) -> int:
    async with get_session() as db:
        companies = await list_companies(db)

    sent_count = 0
    for company in companies:
        try:
            sent = await send_daily_report_for_company(company.id, target_date)
            if sent:
                sent_count += 1
        except Exception:
            log_exception(logger, "daily_report.send_all.company_failed", company_id=company.id)

    log_info(logger, "daily_report.send_all.done", target_date=target_date.isoformat(), sent_count=sent_count)
    return sent_count


def _next_report_time(reference: datetime | None = None) -> datetime:
    now = (reference or ufa_now()).astimezone(UFA_TZ)
    target = now.replace(hour=DAILY_REPORT_HOUR, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


class DailyReportRunner:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._state_lock = asyncio.Lock()
        self._stop_event: asyncio.Event | None = None
        self._sent_dates: dict[int, date] = {}

    async def start(self) -> None:
        async with self._state_lock:
            if self._task is not None and not self._task.done():
                log_info(logger, "daily_report.runner.start.skipped", reason="already_running")
                return
            self._stop_event = asyncio.Event()
            self._task = asyncio.create_task(self._run_loop())
            log_info(logger, "daily_report.runner.started")

    async def stop(self) -> None:
        async with self._state_lock:
            task = self._task
            stop_event = self._stop_event
            self._task = None
            self._stop_event = None

        if stop_event is not None:
            stop_event.set()
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        log_info(logger, "daily_report.runner.stopped")

    async def _run_loop(self) -> None:
        while True:
            try:
                now = ufa_now()
                next_fire = _next_report_time(now)
                sleep_seconds = max((next_fire - now).total_seconds(), 1.0)
                log_debug(logger, "daily_report.runner.sleep", sleep_seconds=round(sleep_seconds, 0), next_fire=next_fire.isoformat())

                stop_event = self._stop_event
                if stop_event is None:
                    return

                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=sleep_seconds)
                    log_info(logger, "daily_report.runner.woken_for_stop")
                    return
                except asyncio.TimeoutError:
                    pass

                target_date = (ufa_now() - timedelta(days=1)).date()
                log_info(logger, "daily_report.runner.firing", target_date=target_date.isoformat())
                await send_all_daily_reports(target_date)

            except asyncio.CancelledError:
                log_info(logger, "daily_report.runner.cancelled")
                raise
            except Exception:
                log_exception(logger, "daily_report.runner.failed")
                await asyncio.sleep(60)


daily_report_runner = DailyReportRunner()

__all__ = [
    "DailyReportCallItem",
    "DailyReportData",
    "DailyReportRunner",
    "compute_daily_report",
    "daily_report_runner",
    "send_all_daily_reports",
    "send_daily_report_for_company",
]
