"""create games table

Revision ID: df6987036e84
Revises: 1fbabf9869b1
Create Date: 2024-12-10 21:29:37.263060

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df6987036e84'
down_revision: Union[str, None] = '1fbabf9869b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'games',
        sa.Column('game_id', sa.String, primary_key=True),
        sa.Column('home_team_id', sa.String, sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('away_team_id', sa.String, sa.ForeignKey('teams.team_id'), nullable=False),
        sa.Column('game_date_est', sa.DateTime, nullable=False),
        sa.Column('season', sa.Integer, nullable=False),
        sa.Column('home_team_points', sa.Integer, nullable=False),
        sa.Column('away_team_points', sa.Integer, nullable=False),
        sa.Column('home_win_pct', sa.Numeric, nullable=False),
        sa.Column('home_home_win_pct', sa.Numeric, nullable=False),
        sa.Column('away_win_pct', sa.Numeric, nullable=False),
        sa.Column('away_away_win_pct', sa.Numeric, nullable=False),
        sa.Column('home_last_10_win_pct', sa.Numeric, nullable=True),
        sa.Column('away_last_10_win_pct', sa.Numeric, nullable=True),
        sa.Column('home_team_b2b', sa.Boolean, nullable=True),
        sa.Column('away_team_b2b', sa.Boolean, nullable=True),
        sa.Column('home_team_wins', sa.Boolean, nullable=True),
    )

def downgrade():
    op.drop_table('games')
