import os
import logging as py_logging

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import ASYNC_DB_URL
from src.app.observability import log_exception, log_info
from src.database.logging import setup_sqlalchemy_logging

ECHO_SQL = os.getenv("SQL_ECHO", "0") == "1"
logger = py_logging.getLogger(__name__)


class Base(DeclarativeBase): pass


engine: AsyncEngine = create_async_engine(ASYNC_DB_URL, echo=False, pool_pre_ping=True)
setup_sqlalchemy_logging(engine.sync_engine)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            log_exception(logger, "db.session.rollback", scope="get_session")
            await session.rollback()
            raise
        finally:
            await session.close()
            log_info(logger, "db.session.closed", scope="get_session")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            log_exception(logger, "db.session.rollback", scope="get_db")
            await session.rollback()
            raise
        finally:
            await session.close()
            log_info(logger, "db.session.closed", scope="get_db")
