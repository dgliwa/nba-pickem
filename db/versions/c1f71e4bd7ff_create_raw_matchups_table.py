"""create raw matchups table

Revision ID: c1f71e4bd7ff
Revises: df6987036e84
Create Date: 2024-12-10 22:04:02.166831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f71e4bd7ff'
down_revision: Union[str, None] = 'df6987036e84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'raw_matchups',
        sa.Column('game_id', sa.String, primary_key=True),
        sa.Column('season', sa.Integer, nullable=False),
        sa.Column('game_date_est', sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('raw_matchups')
