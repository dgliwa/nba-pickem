import os
import pandas as pd
from services import db_engine

def retrieve_matchups_df() -> pd.DataFrame:
  if db_engine:
    with db_engine.connect() as con:
      df = pd.read_sql('SELECT GAME_ID, SEASON, GAME_DATE_EST FROM RAW_MATCHUPS', con)
      df.columns = [c.upper() for c in df.columns]

      return df
  elif os.path.exists("data/raw/nba_season_matchups.csv"):
    return pd.read_csv("data/raw/nba_season_matchups.csv", dtype={"GAME_ID": str}, parse_dates=["GAME_DATE_EST"])
  else:
    return pd.DataFrame()

def save_matchups_df(matchups_df):
  matchups_df.drop_duplicates(inplace=True, subset=["GAME_ID"]) 
  if db_engine:
    with db_engine.connect() as con:
      matchups_df.columns = [c.lower() for c in matchups_df.columns]
      matchups_df.to_sql('raw_matchups', con=con, if_exists='append', index=False)
  else:
    if not os.path.exists("data/raw/nba_season_matchups.csv"):
      matchups_df.to_csv("data/raw/nba_season_matchups.csv", index=False)
    else:
      matchups_df.to_csv("data/raw/nba_season_matchups.csv", index=False, mode="a", header=False)
