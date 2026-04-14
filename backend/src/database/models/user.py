from datetime import datetime

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.enums import UserRole, enum_values
from src.database.limits import EMAIL_MAX_LENGTH, PASSWORD_HASH_MAX_LENGTH, PERSON_NAME_MAX_LENGTH, PHONE_NUMBER_MAX_LENGTH
from src.database.mixins import IdPkMixin, TimestampMixin, UfaDateTime


class User(Base, IdPkMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(length=EMAIL_MAX_LENGTH), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(length=PASSWORD_HASH_MAX_LENGTH), nullable=False)

    name: Mapped[str] = mapped_column(String(length=PERSON_NAME_MAX_LENGTH), nullable=False)
    surname: Mapped[str] = mapped_column(String(length=PERSON_NAME_MAX_LENGTH), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_active_at: Mapped[datetime | None] = mapped_column(UfaDateTime(), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    phone_number: Mapped[str | None] = mapped_column(String(length=PHONE_NUMBER_MAX_LENGTH), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=enum_values),
        nullable=False,
        default=UserRole.OWNER,
        server_default=UserRole.OWNER.value,
        index=True,
    )

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    companies_owned: Mapped[list["Company"]] = relationship(
        back_populates="owner",
        foreign_keys="Company.owner_id",
        cascade="all, delete-orphan",
    )
    employee_memberships: Mapped[list["Employee"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Employee.user_id",
    )
    managed_employee_memberships: Mapped[list["Employee"]] = relationship(
        back_populates="manager",
        foreign_keys="Employee.manager_user_id",
    )
    employee_invitations_sent: Mapped[list["EmployeeInvitation"]] = relationship(
        foreign_keys="EmployeeInvitation.invited_by_user_id",
        back_populates="invited_by",
    )
    employee_invitations_accepted: Mapped[list["EmployeeInvitation"]] = relationship(
        foreign_keys="EmployeeInvitation.accepted_by_user_id",
        back_populates="accepted_by",
    )
    transcriptions_uploaded: Mapped[list["Transcription"]] = relationship(
        back_populates="uploaded_by",
        foreign_keys="Transcription.uploaded_by_user_id",
    )
    detected_transcriptions: Mapped[list["Transcription"]] = relationship(
        back_populates="detected_employee_user",
        foreign_keys="Transcription.detected_employee_user_id",
    )
    favorite_transcriptions: Mapped[list["TranscriptionFavorite"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    analyses_created: Mapped[list["Analysis"]] = relationship(
        back_populates="created_by",
        foreign_keys="Analysis.created_by_user_id",
    )
