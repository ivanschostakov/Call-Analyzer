import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from conftest import BACKEND_DIR, event_records
from src.database.logging import setup_sqlalchemy_logging


def test_sqlalchemy_logging_emits_query_commit_and_rollback(caplog) -> None:
    engine = create_engine("sqlite:///:memory:")
    setup_sqlalchemy_logging(engine)
    caplog.set_level(logging.INFO)

    with engine.connect() as connection:
        connection.execute(text("select 1"))

    with Session(engine) as session:
        session.execute(text("select 1"))
        session.commit()
        session.execute(text("select 1"))
        session.rollback()

    assert event_records(caplog, "db.query.start")
    assert event_records(caplog, "db.query.finish")
    assert event_records(caplog, "db.transaction.commit")
    assert event_records(caplog, "db.transaction.rollback")


def test_sqlalchemy_logging_can_be_disabled(caplog, monkeypatch) -> None:
    import src.database.logging as database_logging

    engine = create_engine("sqlite:///:memory:")
    setup_sqlalchemy_logging(engine)
    monkeypatch.setattr(database_logging, "LOG_SQL_ENABLED", False)
    caplog.set_level(logging.INFO)

    with engine.connect() as connection:
        connection.execute(text("select 1"))

    with Session(engine) as session:
        session.execute(text("select 1"))
        session.commit()
        session.execute(text("select 1"))
        session.rollback()

    assert not event_records(caplog, "db.query.start")
    assert not event_records(caplog, "db.query.finish")
    assert not event_records(caplog, "db.transaction.commit")
    assert not event_records(caplog, "db.transaction.rollback")


def test_no_runtime_print_statements_remain() -> None:
    candidates = [BACKEND_DIR / "logger.py", BACKEND_DIR / "run.py", *sorted((BACKEND_DIR / "src").rglob("*.py"))]
    offenders = [path for path in candidates if "print(" in path.read_text(encoding="utf-8")]
    assert offenders == []
