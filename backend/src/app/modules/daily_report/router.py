import logging
from dataclasses import asdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config import ufa_now
from src.app.modules.auth.dependencies import get_current_user
from src.app.modules.common import get_team_manageable_company_or_404
from src.app.services.daily_report import compute_daily_report
from src.database import get_db
from src.database.crud import list_analyses_for_daily_report
from src.database.models import User

logger = logging.getLogger(__name__)

daily_report_router = APIRouter(prefix="/companies/{company_id}/daily-report", tags=["daily-report"])


class DailyReportCallItemResponse(BaseModel):
    analysis_id: int
    call_name: str
    employee_name: str
    score: float
    template_name: str
    call_date: str | None


class DailyReportResponse(BaseModel):
    report_date: str
    average_score: float
    total_calls: int
    best_calls: list[DailyReportCallItemResponse]
    worst_calls: list[DailyReportCallItemResponse]


@daily_report_router.get("/latest", response_model=DailyReportResponse)
async def get_latest_daily_report(
    company_id: int,
    report_date: str | None = Query(default=None, description="YYYY-MM-DD, defaults to yesterday"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DailyReportResponse:
    await get_team_manageable_company_or_404(db, current_user, company_id)

    if report_date:
        try:
            target_date = date.fromisoformat(report_date)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = (ufa_now() - timedelta(days=1)).date()

    analyses = await list_analyses_for_daily_report(db, company_id, target_date)
    report = compute_daily_report(analyses, target_date)

    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No scored calls found for this date.")

    data = asdict(report)
    return DailyReportResponse(**data)
