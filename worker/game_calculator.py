from celery import shared_task
import pandas as pd
import os
from datetime import datetime
from worker.game_predictor import predict_todays_games
from scraping.data import retrieve_games_df


@shared_task(ignore_result=True)
def calculate_game_data():
  games = load_raw_games()
  games = calculate_b2bs(games)
  games = calculate_game_lookback_data(games)
  os.makedirs("data/processed", exist_ok=True)
  games.to_csv("data/processed/nba_games.csv", index=False)
  predict_todays_games.delay()



def load_raw_games():
  games = retrieve_games_df()
  games["GAME_DATETIME"] = games["GAME_DATE_EST"].astype(int)
  current_year = datetime.now().year
  if datetime.now().month <= 8:
    current_year -= 1
  return games[games["SEASON"] == current_year]

def calculate_b2bs(games):
  games[["HOME_TEAM_B2B", "AWAY_TEAM_B2B"]] = games.apply(lambda game: get_b2bs(game, games), axis=1)
  return games


def get_b2bs(game, games):
  date = game['GAME_DATE_EST'] - pd.Timedelta(days=1)
  home_team = game['HOME_TEAM_ID']
  away_team = game['AWAY_TEAM_ID']
  home_b2b = len(games.loc[(games['GAME_DATE_EST'] == date) & ((games['HOME_TEAM_ID'] == home_team) | (games['AWAY_TEAM_ID'] == home_team))])
  away_b2b = len(games.loc[(games['GAME_DATE_EST'] == date) & ((games['HOME_TEAM_ID'] == away_team) | (games['AWAY_TEAM_ID'] == away_team))])
  return pd.Series([bool(home_b2b), bool(away_b2b)])

def calculate_game_lookback_data(games):
  return pd.concat(games.sort_values("GAME_DATE_EST").apply(lambda row: get_game_lookback_data(row, games), axis=1).to_list())

def get_last_n_win_pct(team_id, n, games):
  _game = games[(games['HOME_TEAM_ID'] == team_id) | (games['AWAY_TEAM_ID'] == team_id)]
  _game.loc[:,'IS_HOME'] = _game['HOME_TEAM_ID'] == team_id
  _game.loc[:,'WIN_PRCT'] = _game['IS_HOME'] == _game['HOME_TEAM_WINS']
  rolling_win_pct = _game["WIN_PRCT"].rolling(n, min_periods=1).mean().rename(f"LAST_{n}_WIN_PCT")
  return pd.concat([_game["GAME_ID"], rolling_win_pct], axis=1)

def get_game_lookback_data(game, games):
  home_team_id = game['HOME_TEAM_ID']
  home_last_10_win_pct = get_last_n_win_pct(home_team_id, 10, games)
  home_last_10_win_pct = home_last_10_win_pct[home_last_10_win_pct["GAME_ID"] == game["GAME_ID"]]
  home_last_10_win_pct.drop(columns="GAME_ID", inplace=True)
  home_lookback_data = pd.concat([home_last_10_win_pct], axis=1).add_prefix('HOME_')

  away_team_id = game['AWAY_TEAM_ID']
  away_last_10_win_pct = get_last_n_win_pct(away_team_id, 10, games)
  away_last_10_win_pct = away_last_10_win_pct[away_last_10_win_pct["GAME_ID"] == game["GAME_ID"]]
  away_last_10_win_pct.drop(columns="GAME_ID", inplace=True)
  away_lookback_data = pd.concat([away_last_10_win_pct], axis=1).add_prefix('AWAY_')

  lookback_data = pd.concat([game.to_frame().T, home_lookback_data, away_lookback_data], axis=1)
  lookback_data["HOME_TEAM_WINS"] = lookback_data["HOME_TEAM_WINS"].astype(bool)
  return lookback_data



