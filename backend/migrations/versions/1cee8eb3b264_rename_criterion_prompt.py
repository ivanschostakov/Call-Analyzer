"""rename criterion prompt

Revision ID: 1cee8eb3b264
Revises: d16075fa5c77
Create Date: 2026-03-30 11:16:08.555887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1cee8eb3b264'
down_revision: Union[str, Sequence[str], None] = 'd16075fa5c77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("criteria", "promt", new_column_name="prompt")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("criteria", "prompt", new_column_name="promt")
