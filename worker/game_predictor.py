from celery import shared_task
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import pickle
from services import redis_client


@shared_task(ignore_result=True)
def predict_todays_games():
  model = load_model()
  teams = load_teams()
  previous_games = load_previous_game_data()
  games_response = retrieve_todays_games()
  todays_games = calculate_todays_game_df(games_response, previous_games)
  todays_games = calculate_game_predictions(todays_games, model)
  todays_games = combine_team_data_with_predictions(teams, todays_games)
  save_predictions(todays_games)


def load_model():
  return pickle.load(open('worker/nba_model.pkl', 'rb'))


def load_teams():
  return pd.read_csv('data/raw/nba_teams.csv')


def load_previous_game_data():
  return pd.read_csv('data/processed/nba_games.csv')


def retrieve_todays_games():
  HEADERS = {
  "Referer": "stats.nba.com",
  "Content-Type": "application/json",
  "Accept": "*/*",
  "Accept-Encoding": "gzip, deflate, br",
  "Connection": "keep-alive",
  "Host": "stats.nba.com",
  "Origin": "https://stats.nba.com",
  "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:70.0) Gecko/20100101 Firefox/70.0",
  }
  eastern = ZoneInfo('US/Eastern')
  current_date = datetime.now(eastern).strftime('%m/%d/%Y')
  url = f"https://stats.nba.com/stats/scoreboardV2?DayOffset=0&LeagueID=00&gameDate={current_date}"

  return requests.get(url, headers=HEADERS).json()


def calculate_todays_game_df(games_response, previous_games):
  results = games_response['resultSets']
  game_headers = results[0]
  eastern_standings = results[4]
  western_standings = results[5]

  games = []
  for game in game_headers.get('rowSet'):
    home_team_id = game[6]
    away_team_id = game[7]

    if home_team_id in [r[0] for r in eastern_standings.get("rowSet")]:
        home_team_rank = next((team for team in eastern_standings.get("rowSet") if team[0] == home_team_id))
    else:
        home_team_rank = next((team for team in western_standings.get("rowSet") if team[0] == home_team_id))

    if away_team_id in [r[0] for r in eastern_standings.get("rowSet")]:
        away_team_rank = next((team for team in eastern_standings.get("rowSet") if team[0] == away_team_id))
    else:
        away_team_rank = next((team for team in western_standings.get("rowSet") if team[0] == away_team_id))

    home_win_pct = home_team_rank[9]
    home_home_wins, home_home_losses = home_team_rank[10].split("-")
    home_home_win_pct = int(home_home_wins) / (int(home_home_wins) + int(home_home_losses)) if int(home_home_wins) + int(home_home_losses) > 0 else 0

    away_win_pct = away_team_rank[9]
    away_away_wins, away_away_losses = away_team_rank[11].split("-")
    away_away_win_pct = int(away_away_wins) / (int(away_away_wins) + int(away_away_losses)) if int(away_away_wins) + int(away_away_losses) > 0 else 0

    game_date = datetime.strptime(game[0], "%Y-%m-%dT%H:%M:%S")
    yesterday = game_date - pd.Timedelta(days=1)

    home_yesterday_game_count = len(previous_games[(previous_games['GAME_DATE_EST'] == yesterday) & ((previous_games['HOME_TEAM_ID'] == home_team_id) | (previous_games["AWAY_TEAM_ID"] == home_team_id))])
    home_b2b = home_yesterday_game_count > 0

    away_yesterday_game_count = len(previous_games[(previous_games['GAME_DATE_EST'] == yesterday) & ((previous_games['HOME_TEAM_ID'] == away_team_id) | (previous_games["AWAY_TEAM_ID"] == away_team_id))])
    away_b2b = away_yesterday_game_count > 0

    home_last_10_win_pct = get_last_n_win_pct(home_team_id, 10, previous_games)
    away_last_10_win_pct = get_last_n_win_pct(away_team_id, 10, previous_games)


    games.append({
        "GAME_DATETIME": int(game_date.timestamp()) * 10**9,
        "HOME_TEAM_ID": home_team_id,
        "AWAY_TEAM_ID": away_team_id,
        "HOME_WIN_PCT": home_win_pct,
        "HOME_HOME_WIN_PCT": home_home_win_pct,
        "AWAY_WIN_PCT": away_win_pct,
        "AWAY_AWAY_WIN_PCT": away_away_win_pct,
        "HOME_TEAM_B2B": home_b2b,
        "AWAY_TEAM_B2B": away_b2b,
        "HOME_LAST_10_WIN_PCT": home_last_10_win_pct,
        "AWAY_LAST_10_WIN_PCT": away_last_10_win_pct
    })
  return pd.DataFrame(games)


def get_last_n_win_pct(team_id, n, previous_games):
  _game = previous_games[(previous_games['HOME_TEAM_ID'] == team_id) | (previous_games['AWAY_TEAM_ID'] == team_id)]
  _game['IS_HOME'] = _game['HOME_TEAM_ID'] == team_id
  _game['WIN_PRCT'] = _game['IS_HOME'] == _game['HOME_TEAM_WINS']
  return _game["WIN_PRCT"].tail(n).mean()


def calculate_game_predictions(games, model):
  games["PREDICTION"] = model.predict(games)
  return games


def combine_team_data_with_predictions(teams, games_with_predictions):
  games_with_predictions = games_with_predictions.merge(teams, left_on="HOME_TEAM_ID", right_on="TEAM_ID")
  games_with_predictions = games_with_predictions.merge(teams, left_on="AWAY_TEAM_ID", right_on="TEAM_ID", suffixes=("_HOME", "_AWAY"))
  games_with_predictions.drop(columns=["TEAM_ID_HOME", "TEAM_ID_AWAY"], inplace=True)
  games_with_predictions["WINNER"] = games_with_predictions.apply(prettify_winner, axis=1)
  games_with_predictions["GAME_DATE_EST"] = pd.to_datetime(games_with_predictions["GAME_DATETIME"], unit='ns').dt.strftime('%Y-%m-%d')

  return games_with_predictions[["GAME_DATE_EST", "ABBREVIATION_HOME", "NICKNAME_HOME", "ABBREVIATION_AWAY", "NICKNAME_AWAY", "WINNER"]]


def prettify_winner(row):
    if row["PREDICTION"] == 1:
        return f"{row['ABBREVIATION_HOME']} {row['NICKNAME_HOME']}"
    else:
        return f"{row['ABBREVIATION_AWAY']} {row['NICKNAME_AWAY']}"

def save_predictions(todays_games):
  todays_games_json = todays_games.to_json(orient='records')
  redis_client.setex('todays_games', 3600, todays_games_json)
