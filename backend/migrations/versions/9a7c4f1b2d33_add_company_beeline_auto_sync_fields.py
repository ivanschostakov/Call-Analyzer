"""add company beeline auto sync fields

Revision ID: 9a7c4f1b2d33
Revises: 5b45c3d9a4ee
Create Date: 2026-04-01 16:35:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "9a7c4f1b2d33"
down_revision: str | Sequence[str] | None = "5b45c3d9a4ee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("beeline_last_auto_sync_target_date", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column("beeline_last_auto_sync_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("beeline_last_auto_sync_finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("beeline_last_auto_sync_status", sa.String(length=32), nullable=True))
    op.add_column("companies", sa.Column("beeline_last_auto_sync_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "beeline_last_auto_sync_error")
    op.drop_column("companies", "beeline_last_auto_sync_status")
    op.drop_column("companies", "beeline_last_auto_sync_finished_at")
    op.drop_column("companies", "beeline_last_auto_sync_started_at")
    op.drop_column("companies", "beeline_last_auto_sync_target_date")
