import os
import pandas as pd
from services import db_engine

def retrieve_matchups_df() -> pd.DataFrame:
  if db_engine:
    with db_engine.connect() as con:
      df = pd.read_sql('SELECT GAME_ID, SEASON, GAME_DATE_EST, TEAM_ID FROM RAW_MATCHUPS', con)
      df.columns = [c.upper() for c in df.columns]
      return df
  elif os.path.exists("data/raw/nba_season_matchups.csv"):
    return pd.read_csv("data/raw/nba_season_matchups.csv", dtype={"GAME_ID": str})
  else:
    return pd.DataFrame()
