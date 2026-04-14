from os import getenv
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from sqlalchemy.engine import URL

BACKEND_DIR = Path(__file__).resolve().parent

load_dotenv(BACKEND_DIR / ".env")


def env_flag(name: str, default: bool) -> bool:
    raw_value = getenv(name)
    if raw_value is None: return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def env_csv(name: str) -> list[str]:
    raw_value = getenv(name, "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def normalize_origin(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return normalized

POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD")
POSTGRES_USER = getenv("POSTGRES_USER")
POSTGRES_HOST = getenv("POSTGRES_HOST")
POSTGRES_PORT = getenv("POSTGRES_PORT")
POSTGRES_DB = getenv("POSTGRES_DB")
ASYNC_DB_URL = URL.create(
    "postgresql+asyncpg",
    username=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=int(POSTGRES_PORT) if POSTGRES_PORT else None,
    database=POSTGRES_DB,
)

OPENAI_API_KEY = getenv("OPENAI_API_KEY")
OPENAI_MODEL = getenv("OPENAI_MODEL")
OPENAI_HTTP_PROXY = getenv("OPENAI_HTTP_PROXY")
WHISPER_MODEL = getenv("WHISPER_MODEL")
OPENAI_TRANSCRIBE_MODEL = getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe")
USE_LOCAL_TRANSCRIBER = env_flag("USE_LOCAL_TRANSCRIBER", True)

BEELINE_API_BASE_URL = (getenv("BEELINE_API_BASE_URL") or "https://cloudpbx.beeline.ru/apis/portal").rstrip("/")
BEELINE_API_TIMEOUT_SECONDS = float(getenv("BEELINE_API_TIMEOUT_SECONDS", 30))

REFRESH_TOKEN_LIFETIME_DAYS = int(getenv("REFRESH_TOKEN_LIFETIME_DAYS", 30))
JWT_ACCESS_EXPIRE_MINUTES = int(getenv("JWT_ACCESS_EXPIRE_MINUTES", 15))
JWT_ACCESS_SECRET_KEY = getenv("JWT_ACCESS_SECRET_KEY")
EMPLOYEE_INVITATION_LIFETIME_DAYS = int(getenv("EMPLOYEE_INVITATION_LIFETIME_DAYS", 7))
FRONTEND_BASE_URL = (getenv("FRONTEND_BASE_URL") or "http://127.0.0.1:5173").rstrip("/")
CORS_ALLOWED_ORIGINS = [normalize_origin(item) for item in env_csv("CORS_ALLOWED_ORIGINS")] or [normalize_origin(FRONTEND_BASE_URL)]

SMTP_HOST = getenv("SMTP_HOST")
SMTP_PORT = int(getenv("SMTP_PORT", 587))
SMTP_USERNAME = getenv("SMTP_USERNAME")
SMTP_PASSWORD = getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = getenv("SMTP_FROM_EMAIL") or SMTP_USERNAME
SMTP_FROM_NAME = getenv("SMTP_FROM_NAME", "Call Analyzer")
SMTP_USE_TLS = getenv("SMTP_USE_TLS", "1") == "1"
SMTP_USE_SSL = getenv("SMTP_USE_SSL", "0") == "1"
UFA_TZ = ZoneInfo("Asia/Yekaterinburg")

LOG_LEVEL = getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE_MAX_BYTES = int(getenv("LOG_FILE_MAX_BYTES", 10 * 1024 * 1024))
LOG_FILE_BACKUP_COUNT = int(getenv("LOG_FILE_BACKUP_COUNT", 5))
LOG_SQL_ENABLED = env_flag("LOG_SQL_ENABLED", False)
LOG_HTTP_BODY_ENABLED = env_flag("LOG_HTTP_BODY_ENABLED", False)
LOG_ANALYZER_PAYLOADS_ENABLED = env_flag("LOG_ANALYZER_PAYLOADS_ENABLED", False)
LOG_TRANSCRIPTS_ENABLED = env_flag("LOG_TRANSCRIPTS_ENABLED", False)
LOG_HTTP_BODY_MAX_BYTES = int(getenv("LOG_HTTP_BODY_MAX_BYTES", 64 * 1024))
UPLOAD_MAX_BYTES = int(getenv("UPLOAD_MAX_BYTES", 25 * 1024 * 1024))
TRANSCRIPTION_JOB_CONCURRENCY = max(int(getenv("TRANSCRIPTION_JOB_CONCURRENCY", 3)), 1)

def ufa_now() -> datetime: return datetime.now(UFA_TZ)

WORKING_DIR = BACKEND_DIR
LOGS_DIR = WORKING_DIR / "logs"
MEDIA_DIR = WORKING_DIR / "media"
UPLOADS_DIR = MEDIA_DIR / "uploads"
COMPANIES_UPLOAD_DIR = UPLOADS_DIR / "companies"
