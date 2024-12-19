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
    return pd.read_csv("data/raw/nba_games.csv", dtype={"GAME_ID": str}, parse_dates=["GAME_DATE_EST"])
  else:
    return pd.DataFrame()


def save_games_df(games_df):
  games_df.drop_duplicates(inplace=True, subset=["GAME_ID"])
  if db_engine:
    with db_engine.connect() as con:
      games_df.columns = [c.lower() for c in games_df.columns]
      games_df.to_sql('games', con=con, if_exists='append', index=False)
  else:
    if not os.path.exists("data/raw/nba_games.csv"):
      games_df.to_csv("data/raw/nba_games.csv", index=False)
    else:
      games_df.to_csv("data/raw/nba_games.csv", index=False, mode="a", header=False)
