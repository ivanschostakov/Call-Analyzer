"""add company beeline integration settings

Revision ID: 5b45c3d9a4ee
Revises: e2d0b8a9c4f1
Create Date: 2026-03-31 00:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5b45c3d9a4ee"
down_revision: Union[str, Sequence[str], None] = "e2d0b8a9c4f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("companies", sa.Column("beeline_api_token", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column("beeline_auto_export_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("companies", sa.Column("beeline_auto_analysis_template_id", sa.BigInteger(), nullable=True))
    op.add_column("companies", sa.Column("beeline_last_sync_target_date", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column("beeline_last_sync_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("beeline_last_sync_finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("beeline_last_sync_status", sa.String(length=32), nullable=True))
    op.add_column("companies", sa.Column("beeline_last_sync_error", sa.Text(), nullable=True))
    op.create_index(op.f("ix_companies_beeline_auto_analysis_template_id"), "companies", ["beeline_auto_analysis_template_id"], unique=False)
    op.create_foreign_key(
        "fk_companies_beeline_auto_analysis_template_id_templates",
        "companies",
        "templates",
        ["beeline_auto_analysis_template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_companies_beeline_auto_analysis_template_id_templates", "companies", type_="foreignkey")
    op.drop_index(op.f("ix_companies_beeline_auto_analysis_template_id"), table_name="companies")
    op.drop_column("companies", "beeline_last_sync_error")
    op.drop_column("companies", "beeline_last_sync_status")
    op.drop_column("companies", "beeline_last_sync_finished_at")
    op.drop_column("companies", "beeline_last_sync_started_at")
    op.drop_column("companies", "beeline_last_sync_target_date")
    op.drop_column("companies", "beeline_auto_analysis_template_id")
    op.drop_column("companies", "beeline_auto_export_enabled")
    op.drop_column("companies", "beeline_api_token")
