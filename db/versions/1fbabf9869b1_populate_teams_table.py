"""populate teams table

Revision ID: 1fbabf9869b1
Revises: 07c8ca775bb8
Create Date: 2024-12-10 21:10:08.313041

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.sql import table, column
import sqlalchemy as sa
import pandas as pd



# revision identifiers, used by Alembic.
revision: str = '1fbabf9869b1'
down_revision: Union[str, None] = '07c8ca775bb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

teams = table('teams',
    column('id', sa.String),
    column('league_id', sa.String(2)),
    column('abbreviation', sa.String(3)),
    column('city', sa.String(120)),
    column('nickname', sa.String(120))
)


def upgrade() -> None:
    connection = op.get_bind()
    teams_pd = pd.read_csv('data/raw/nba_teams.csv', dtype={'LEAGUE_ID': str})
    for _, team in teams_pd.iterrows():
        connection.execute(
            teams.insert().values(
                id= team["TEAM_ID"],
                league_id=team["LEAGUE_ID"],
                abbreviation=team["ABBREVIATION"],
                city=team["CITY"],
                nickname=team["NICKNAME"]
            )
        )
    pass


def downgrade() -> None:
    pass
