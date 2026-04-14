"""add detected employee user to transcriptions

Revision ID: a2f7d3c4b981
Revises: 8b7e2c1d4a91
Create Date: 2026-04-07 16:20:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a2f7d3c4b981"
down_revision: str | Sequence[str] | None = "8b7e2c1d4a91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transcriptions", sa.Column("detected_employee_user_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_transcriptions_detected_employee_user_id"), "transcriptions", ["detected_employee_user_id"], unique=False)
    op.create_foreign_key(
        "fk_transcriptions_detected_employee_user_id_users",
        "transcriptions",
        "users",
        ["detected_employee_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_transcriptions_detected_employee_user_id_users", "transcriptions", type_="foreignkey")
    op.drop_index(op.f("ix_transcriptions_detected_employee_user_id"), table_name="transcriptions")
    op.drop_column("transcriptions", "detected_employee_user_id")
