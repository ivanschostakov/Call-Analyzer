import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-test")
os.environ.setdefault("WHISPER_MODEL", "tiny")
os.environ.setdefault("JWT_ACCESS_SECRET_KEY", "test-secret")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@example.com")
os.environ.setdefault("LOG_SQL_ENABLED", "1")
os.environ.setdefault("LOG_HTTP_BODY_ENABLED", "1")
os.environ.setdefault("LOG_ANALYZER_PAYLOADS_ENABLED", "1")
os.environ.setdefault("LOG_TRANSCRIPTS_ENABLED", "1")

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def event_records(caplog, event_name: str):
    return [record for record in caplog.records if record.getMessage() == event_name]
