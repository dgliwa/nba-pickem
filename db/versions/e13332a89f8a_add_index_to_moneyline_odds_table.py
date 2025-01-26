"""add index to moneyline odds table

Revision ID: e13332a89f8a
Revises: e794aa6813ad
Create Date: 2025-01-26 11:48:32.522950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e13332a89f8a'
down_revision: Union[str, None] = 'e794aa6813ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_moneyline_odds_game_id", "moneyline_odds", ["game_id"])


def downgrade() -> None:
    op.drop_index("idx_moneyline_odds_game_id")
