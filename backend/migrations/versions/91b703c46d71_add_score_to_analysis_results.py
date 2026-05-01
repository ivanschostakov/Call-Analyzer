"""add score to analysis results

Revision ID: 91b703c46d71
Revises: d4f8a61c7b2d
Create Date: 2026-04-28 21:19:09.608689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '91b703c46d71'
down_revision: Union[str, Sequence[str], None] = 'd4f8a61c7b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('analysis_results', sa.Column('score', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('analysis_results', 'score')
