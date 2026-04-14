"""make template instructions required

Revision ID: 4e0e031441fb
Revises: 39c624c04baf
Create Date: 2026-03-30 12:52:19.660028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e0e031441fb'
down_revision: Union[str, Sequence[str], None] = '39c624c04baf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    templates = sa.table(
        "templates",
        sa.column("id", sa.BigInteger()),
        sa.column("instructions", sa.Text()),
    )

    missing_count = bind.execute(
        sa.select(sa.func.count())
        .select_from(templates)
        .where(templates.c.instructions.is_(None))
    ).scalar_one()
    if missing_count:
        raise RuntimeError("templates.instructions contains NULL values; populate them explicitly before applying this migration.")

    op.alter_column("templates", "instructions", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("templates", "instructions", existing_type=sa.Text(), nullable=True)
