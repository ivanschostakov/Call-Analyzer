import logging as py_logging

from time import perf_counter

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from config import LOG_SQL_ENABLED
from src.app.observability import log_exception, log_info


logger = py_logging.getLogger(__name__)
_session_logging_configured = False


def setup_sqlalchemy_logging(engine: Engine) -> None:
    global _session_logging_configured
    if getattr(engine, "_codex_logging_configured", False):
        return

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        context._query_started_at = perf_counter()
        if LOG_SQL_ENABLED:
            log_info(
                logger,
                "db.query.start",
                statement=statement,
                parameters=parameters,
                executemany=executemany,
            )

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        if LOG_SQL_ENABLED:
            started_at = getattr(context, "_query_started_at", perf_counter())
            log_info(
                logger,
                "db.query.finish",
                statement=statement,
                rowcount=cursor.rowcount,
                duration_ms=round((perf_counter() - started_at) * 1000, 3),
                executemany=executemany,
            )

    @event.listens_for(engine, "handle_error")
    def handle_error(exception_context):  # noqa: ANN001
        log_exception(
            logger,
            "db.query.error",
            statement=exception_context.statement,
            parameters=exception_context.parameters,
            original_exception=str(exception_context.original_exception),
        )

    if not _session_logging_configured:
        @event.listens_for(Session, "after_commit")
        def after_commit(session):  # noqa: ANN001
            if LOG_SQL_ENABLED:
                log_info(
                    logger,
                    "db.transaction.commit",
                    new=len(session.new),
                    dirty=len(session.dirty),
                    deleted=len(session.deleted),
                    identity_map_size=len(session.identity_map),
                )

        @event.listens_for(Session, "after_rollback")
        def after_rollback(session):  # noqa: ANN001
            if LOG_SQL_ENABLED:
                log_info(
                    logger,
                    "db.transaction.rollback",
                    new=len(session.new),
                    dirty=len(session.dirty),
                    deleted=len(session.deleted),
                    identity_map_size=len(session.identity_map),
                )

        _session_logging_configured = True

    engine._codex_logging_configured = True
