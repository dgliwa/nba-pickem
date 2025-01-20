"""change moneyline table to composite primary key

Revision ID: 950822567857
Revises: 98ee3c387120
Create Date: 2025-01-20 16:29:59.212172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '950822567857'
down_revision: Union[str, None] = '98ee3c387120'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE moneyline_odds DROP CONSTRAINT moneyline_odds_pkey")
    op.execute("ALTER TABLE moneyline_odds ADD PRIMARY KEY (game_id, sportsbook)")
    


def downgrade() -> None:
    op.execute("ALTER TABLE moneyline_odds DROP CONSTRAINT moneyline_odds_pkey")
    op.execute("ALTER TABLE moneyline_odds ADD PRIMARY KEY game_id")
