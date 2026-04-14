"""tighten analysis strictness

Revision ID: 39c624c04baf
Revises: c9a1c1d5924b
Create Date: 2026-03-30 12:48:16.940394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39c624c04baf'
down_revision: Union[str, Sequence[str], None] = 'c9a1c1d5924b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    analyses = sa.table(
        "analyses",
        sa.column("id", sa.BigInteger()),
        sa.column("template_id", sa.BigInteger()),
        sa.column("template_name", sa.String(length=120)),
        sa.column("instructions", sa.Text()),
    )
    templates = sa.table(
        "templates",
        sa.column("id", sa.BigInteger()),
        sa.column("name", sa.String(length=120)),
        sa.column("instructions", sa.Text()),
    )

    bind.execute(
        analyses.update()
        .values(
            template_name=sa.select(templates.c.name).where(templates.c.id == analyses.c.template_id).scalar_subquery(),
            instructions=sa.select(templates.c.instructions).where(templates.c.id == analyses.c.template_id).scalar_subquery(),
        )
        .where(
            sa.and_(
                analyses.c.template_id.is_not(None),
                sa.or_(
                    analyses.c.template_name.is_(None),
                    analyses.c.instructions.is_(None),
                ),
            )
        )
    )

    remaining_nulls = bind.execute(
        sa.select(sa.func.count())
        .select_from(analyses)
        .where(
            sa.or_(
                analyses.c.template_name.is_(None),
                analyses.c.instructions.is_(None),
            )
        )
    ).scalar_one()
    if remaining_nulls:
        raise RuntimeError("analyses.template_name and analyses.instructions must be populated before applying strict constraints.")

    op.alter_column("analyses", "template_name", existing_type=sa.String(length=120), nullable=False)
    op.alter_column("analyses", "instructions", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("analyses", "instructions", existing_type=sa.Text(), nullable=True)
    op.alter_column("analyses", "template_name", existing_type=sa.String(length=120), nullable=True)
