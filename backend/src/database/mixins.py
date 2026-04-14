from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from config import UFA_TZ, ufa_now


class UfaDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UFA_TZ)
        return value.astimezone(UFA_TZ)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UFA_TZ)
        return value.astimezone(UFA_TZ)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UfaDateTime(), nullable=False, default=ufa_now)
    updated_at: Mapped[datetime] = mapped_column(UfaDateTime(), nullable=False, default=ufa_now, onupdate=ufa_now)

class IdPkMixin:
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
