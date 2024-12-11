import os
import pandas as pd
from services import db_engine

def retrieve_games_df() -> pd.DataFrame:
  if db_engine:
    with db_engine.connect() as con:
      df = pd.read_sql('SELECT GAME_ID, HOME_TEAM_ID, AWAY_TEAM_ID, GAME_DATE_EST, SEASON, HOME_TEAM_POINTS, AWAY_TEAM_POINTS, HOME_WIN_PCT, HOME_HOME_WIN_PCT, AWAY_WIN_PCT, AWAY_AWAY_WIN_PCT, HOME_TEAM_WINS FROM GAMES', con)
      df.columns = [c.upper() for c in df.columns]
      return df
  elif os.path.exists("data/raw/nba_games.csv"):
    return pd.read_csv("data/raw/nba_games.csv", dtype={"GAME_ID": str})
  else:
    return pd.DataFrame()
