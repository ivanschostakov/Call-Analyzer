import logging
from logging.handlers import RotatingFileHandler

from config import LOG_FILE_BACKUP_COUNT, LOG_FILE_MAX_BYTES, LOG_LEVEL, LOGS_DIR
from src.app.observability import ContextAwareFormatter


def setup_logging():
    if getattr(setup_logging, "_configured", False):
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    fmt = ContextAwareFormatter(
        fmt="%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = logging.StreamHandler()
    sh.setLevel(LOG_LEVEL)
    sh.setFormatter(fmt)

    file_handler = RotatingFileHandler(
        LOGS_DIR / "backend.log",
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(fmt)

    root.handlers.clear()
    root.addHandler(sh)
    root.addHandler(file_handler)
    setup_logging._configured = True
