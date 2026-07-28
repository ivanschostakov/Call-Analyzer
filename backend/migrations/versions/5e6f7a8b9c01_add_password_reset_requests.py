"""add password reset requests

Revision ID: 5e6f7a8b9c01
Revises: 91b703c46d71
Create Date: 2026-07-28 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "5e6f7a8b9c01"
down_revision: str | Sequence[str] | None = "91b703c46d71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_requests",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_password_reset_requests_id"), "password_reset_requests", ["id"], unique=False)
    op.create_index(op.f("ix_password_reset_requests_user_id"), "password_reset_requests", ["user_id"], unique=False)
    op.create_index(op.f("ix_password_reset_requests_token_hash"), "password_reset_requests", ["token_hash"], unique=True)
    op.create_index(op.f("ix_password_reset_requests_expires_at"), "password_reset_requests", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_password_reset_requests_expires_at"), table_name="password_reset_requests")
    op.drop_index(op.f("ix_password_reset_requests_token_hash"), table_name="password_reset_requests")
    op.drop_index(op.f("ix_password_reset_requests_user_id"), table_name="password_reset_requests")
    op.drop_index(op.f("ix_password_reset_requests_id"), table_name="password_reset_requests")
    op.drop_table("password_reset_requests")
