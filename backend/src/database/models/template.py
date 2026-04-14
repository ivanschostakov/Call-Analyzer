from sqlalchemy import BigInteger, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.database.limits import TEMPLATE_NAME_MAX_LENGTH
from src.database.mixins import IdPkMixin, TimestampMixin
from src.enums import DEFAULT_COMPANY_TEMPLATE


class Template(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_templates_company_name"),
    )

    company_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(length=TEMPLATE_NAME_MAX_LENGTH), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=DEFAULT_COMPANY_TEMPLATE.instructions,
        server_default=DEFAULT_COMPANY_TEMPLATE.instructions,
    )

    company: Mapped["Company"] = relationship(back_populates="templates", foreign_keys=[company_id])
    criteria: Mapped[list["Criterion"]] = relationship(back_populates="template", cascade="all, delete-orphan")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="template")
