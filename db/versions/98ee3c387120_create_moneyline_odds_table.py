"""create moneyline odds table

Revision ID: 98ee3c387120
Revises: b2c91bd8ee23
Create Date: 2024-12-11 18:34:26.165335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98ee3c387120'
down_revision: Union[str, None] = '65a64f7a4b1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'moneyline_odds',
        sa.Column('game_id', sa.String, primary_key=True),
        sa.Column('sportsbook', sa.String, nullable=False),
        sa.Column('home_odds', sa.Integer, nullable=False),
        sa.Column('away_odds', sa.Integer, nullable=False),
    )

def downgrade():
    op.drop_table('moneyline_odds')
