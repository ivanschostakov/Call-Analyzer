from fastapi import APIRouter

from .analysis.router import analysis_router
from .auth.router import auth_router
from .companies.router import companies_router
from .criteria.router import criteria_router
from .employees.router import employees_router
from .mentor.router import mentor_router
from .templates.router import templates_router
from .transcriptions.router import transcriptions_router
from .uploads.router import uploads_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(analysis_router)
api_router.include_router(companies_router)
api_router.include_router(employees_router)
api_router.include_router(mentor_router)
api_router.include_router(templates_router)
api_router.include_router(criteria_router)
api_router.include_router(uploads_router)
api_router.include_router(transcriptions_router)

__all__ = [
    "api_router",
    "analysis_router",
    "auth_router",
    "companies_router",
    "criteria_router",
    "employees_router",
    "mentor_router",
    "templates_router",
    "transcriptions_router",
    "uploads_router",
]
