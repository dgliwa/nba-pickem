import json
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from dao import (
    retrieve_game_predictions_df,
    retrieve_teams_df,
    redis_client,
    retrieve_game_predictions_with_results,
    retrieve_moneylines_df
)
from worker import collect_game_data


def predictions_for_date(game_date=datetime.now(ZoneInfo('US/Eastern')).date()):
    games_str = redis_client.get(f"{game_date.strftime('%Y-%m-%d')}_games")
    if games_str:
        return json.loads(games_str)

    teams = retrieve_teams_df()
    predictions = retrieve_game_predictions_df(game_date)

    predictions_for_date = predictions[predictions["GAME_DATE_EST"] == np.datetime64(game_date)]
    if predictions_for_date.empty:
        collect_game_data.delay()
        return []

    formatted_predictions = _combine_team_data_with_predictions(teams, predictions_for_date)
    _cache_predictions(formatted_predictions, game_date)
    return formatted_predictions.to_dict(orient='records')


def get_historical_accuracy(bet_amount=10.0):
    return retrieve_game_predictions_with_results(bet_amount)


def _combine_team_data_with_predictions(teams, game_predictions):
    game_predictions = game_predictions.merge(teams, left_on="HOME_TEAM_ID", right_on="TEAM_ID")
    game_predictions = game_predictions.merge(teams, left_on="AWAY_TEAM_ID", right_on="TEAM_ID", suffixes=("_HOME", "_AWAY"))
    game_predictions.drop(columns=["TEAM_ID_HOME", "TEAM_ID_AWAY"], inplace=True)
    game_predictions["PREDICTED_WINNER"] = game_predictions.apply(lambda row: _prettify_winner(row, row["PREDICTED_HOME_TEAM_WINS"]), axis=1)
    game_predictions["ACTUAL_WINNER"] = game_predictions.apply(lambda row: _prettify_winner(row, row["HOME_TEAM_WINS"]), axis=1)
    game_predictions["GAME_DATE_EST"] = game_predictions["GAME_DATE_EST"].dt.strftime('%Y-%m-%d')
    return game_predictions[["GAME_ID", "GAME_DATE_EST", "ABBREVIATION_HOME", "NICKNAME_HOME", "ABBREVIATION_AWAY", "NICKNAME_AWAY", "PREDICTED_WINNER", "ACTUAL_WINNER"]]


def _prettify_winner(row, home_team_wins):
    if home_team_wins == 1:
        return f"{row['ABBREVIATION_HOME']} {row['NICKNAME_HOME']}"
    else:
        return f"{row['ABBREVIATION_AWAY']} {row['NICKNAME_AWAY']}"


def _cache_predictions(games, game_date):
    todays_games_json = games.to_json(orient='records')
    redis_client.setex(f"{game_date.strftime('%Y-%m-%d')}_games", 3600, todays_games_json)
