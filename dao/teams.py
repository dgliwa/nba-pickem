import os
import pandas as pd
from dao.db import engine as db_engine


def retrieve_teams_df() -> pd.DataFrame:
    if db_engine:
        with db_engine.connect() as con:
            df = pd.read_sql('SELECT TEAM_ID, LEAGUE_ID, ABBREVIATION, CITY, NICKNAME FROM TEAMS', con)
            df.columns = [c.upper() for c in df.columns]
            df["TEAM_ID"] = df["TEAM_ID"].astype(int)
            return df
    elif os.path.exists("data/raw/nba_teams.csv"):
        return pd.read_csv("data/raw/nba_teams.csv")
    else:
        return pd.DataFrame()


def save_teams_df(teams_df):
    teams_df.drop_duplicates(inplace=True, subset=["TEAM_ID"])
    if db_engine:
        with db_engine.connect() as con:
            teams_df.columns = [c.lower() for c in teams_df.columns]
            teams_df.to_sql('teams', con=con, if_exists='replace', index=False)
    else:
        teams_df.to_csv("data/raw/nba_teams.csv", index=False)
