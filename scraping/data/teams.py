import os
import pandas as pd
from services import db_engine

def retrieve_teams_df() -> pd.DataFrame:
  if db_engine:
    with db_engine.connect() as con:
      df = pd.read_sql('SELECT TEAM_ID, LEAGUE_ID, ABBREVIATION, CITY, NICKNAME FROM TEAMS', con)
      df.columns = [c.upper() for c in df.columns]
      return df
  elif os.path.exists("data/raw/nba_teams.csv"):
    return pd.read_csv("data/raw/nba_teams.csv")
  else:
    return pd.DataFrame()
