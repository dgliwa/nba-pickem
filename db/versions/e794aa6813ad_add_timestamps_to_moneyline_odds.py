"""add timestamps to moneyline odds

Revision ID: e794aa6813ad
Revises: 8d40020d19c3
Create Date: 2025-01-23 20:36:12.337398

"""
from typing import Sequence, Union 
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e794aa6813ad'
down_revision: Union[str, None] = '8d40020d19c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'moneyline_odds_temp',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('game_id', sa.String, nullable=False),
        sa.Column('sportsbook', sa.String, nullable=False),
        sa.Column('home_odds', sa.Integer, nullable=False),
        sa.Column('away_odds', sa.Integer, nullable=False),
        sa.Column('game_date_est', sa.DateTime, nullable=False),
        sa.Column('line_datetime', sa.DateTime, nullable=True),
    )
    
    op.execute("INSERT INTO moneyline_odds_temp (game_id, sportsbook, home_odds, away_odds, game_date_est) SELECT game_id, sportsbook, home_odds, away_odds, game_date_est FROM moneyline_odds")
    
    op.drop_table('moneyline_odds')
    
    op.create_table(
        'moneyline_odds',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('game_id', sa.String, nullable=False),
        sa.Column('sportsbook', sa.String, nullable=False),
        sa.Column('home_odds', sa.Integer, nullable=False),
        sa.Column('away_odds', sa.Integer, nullable=False),
        sa.Column('game_date_est', sa.DateTime, nullable=False),
        sa.Column('line_datetime', sa.DateTime, nullable=True),
    )
    
    op.execute("INSERT INTO moneyline_odds (id, game_id, sportsbook, home_odds, away_odds, game_date_est, line_datetime) SELECT id, game_id, sportsbook, home_odds, away_odds, game_date_est, line_datetime FROM moneyline_odds_temp")
    op.execute("SELECT setval('moneyline_odds_id_seq', (SELECT MAX(id) from moneyline_odds))")
    
    op.drop_table('moneyline_odds_temp')
    


def downgrade() -> None:
    op.drop_column("moneyline_odds", "line_datetime")
    op.execute("ALTER TABLE moneyline_odds DROP CONSTRAINT moneyline_odds_pkey")
    op.drop_column("moneyline_odds", "id")
    op.execute("ALTER TABLE moneyline_odds ADD PRIMARY KEY (game_id, sportsbook)")
    
