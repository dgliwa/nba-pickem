"""add game features to prediction models

Revision ID: 8d40020d19c3
Revises: 950822567857
Create Date: 2025-01-22 08:02:46.902002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d40020d19c3'
down_revision: Union[str, None] = '950822567857'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("game_predictions", sa.Column("home_win_pct", sa.DECIMAL))
    op.add_column("game_predictions", sa.Column("home_home_win_pct", sa.DECIMAL))
    op.add_column("game_predictions", sa.Column("away_win_pct", sa.DECIMAL))
    op.add_column("game_predictions", sa.Column("away_away_win_pct", sa.DECIMAL))
    op.add_column("game_predictions", sa.Column("home_team_b2b", sa.BOOLEAN))
    op.add_column("game_predictions", sa.Column("away_team_b2b", sa.BOOLEAN))
    op.add_column("game_predictions", sa.Column("home_last_10_win_pct", sa.DECIMAL))
    op.add_column("game_predictions", sa.Column("away_last_10_win_pct", sa.DECIMAL))


def downgrade() -> None:
    op.drop_column("game_predictions", "home_win_pct")
    op.drop_column("game_predictions", "home_home_win_pct")
    op.drop_column("game_predictions", "away_win_pct")
    op.drop_column("game_predictions", "away_away_win_pct")
    op.drop_column("game_predictions", "home_team_b2b")
    op.drop_column("game_predictions", "away_team_b2b")
    op.drop_column("game_predictions", "home_last_10_win_pct")
    op.drop_column("game_predictions", "away_last_10_win_pct")
