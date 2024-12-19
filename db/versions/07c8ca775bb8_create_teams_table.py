"""create teams table

Revision ID: 07c8ca775bb8
Revises: 
Create Date: 2024-12-10 19:54:25.269342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07c8ca775bb8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'teams',
        sa.Column('team_id', sa.String, primary_key=True),
        sa.Column('league_id', sa.String(2), nullable=False),
        sa.Column('abbreviation', sa.String(3), nullable=False),
        sa.Column('city', sa.String(120), nullable=False),
        sa.Column('nickname', sa.String(120), nullable=False)
    )

def downgrade():
    op.drop_table('teams')

