"""create game predictions table

Revision ID: 65a64f7a4b1a
Revises: c1f71e4bd7ff
Create Date: 2024-12-11 14:52:29.227559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65a64f7a4b1a'
down_revision: Union[str, None] = 'c1f71e4bd7ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'game_predictions',
        sa.Column('game_id', sa.String, primary_key=True),
        sa.Column('predicted_home_team_wins', sa.Boolean, nullable=False),
        sa.Column('game_date_est', sa.DateTime, nullable=False),
    )


def downgrade():
    op.drop_table('game_predictions')
