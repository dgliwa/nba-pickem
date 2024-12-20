import json
from datetime import datetime
import numpy as np
from dao import retrieve_game_predictions_df, retrieve_teams_df, redis_client, retrieve_game_predictions_with_results
from worker import collect_game_data


def assemble_todays_predictions():
    todays_games_str = redis_client.get("todays_games")
    if todays_games_str:
        return json.loads(todays_games_str)

    teams = retrieve_teams_df()
    predictions = retrieve_game_predictions_df()

    current_date = datetime.now().date()
    todays_predictions = predictions[predictions["GAME_DATE_EST"] == np.datetime64(current_date)]
    if todays_predictions.empty:
        collect_game_data.delay()
        return []

    formatted_predictions = _combine_team_data_with_predictions(teams, todays_predictions)
    _cache_predictions(formatted_predictions)
    return formatted_predictions.to_dict(orient='records')


def get_historical_accuracy():
    return retrieve_game_predictions_with_results()


def _combine_team_data_with_predictions(teams, game_predictions):
    game_predictions = game_predictions.merge(teams, left_on="HOME_TEAM_ID", right_on="TEAM_ID")
    game_predictions = game_predictions.merge(teams, left_on="AWAY_TEAM_ID", right_on="TEAM_ID", suffixes=("_HOME", "_AWAY"))
    game_predictions.drop(columns=["TEAM_ID_HOME", "TEAM_ID_AWAY"], inplace=True)
    game_predictions["WINNER"] = game_predictions.apply(_prettify_winner, axis=1)
    game_predictions["GAME_DATE_EST"] = game_predictions["GAME_DATE_EST"].dt.strftime('%Y-%m-%d')
    return game_predictions[["GAME_DATE_EST", "ABBREVIATION_HOME", "NICKNAME_HOME", "ABBREVIATION_AWAY", "NICKNAME_AWAY", "WINNER"]]


def _prettify_winner(row):
    if row["PREDICTED_HOME_TEAM_WINS"] == 1:
        return f"{row['ABBREVIATION_HOME']} {row['NICKNAME_HOME']}"
    else:
        return f"{row['ABBREVIATION_AWAY']} {row['NICKNAME_AWAY']}"


def _cache_predictions(todays_games):
    todays_games_json = todays_games.to_json(orient='records')
    redis_client.setex('todays_games', 3600, todays_games_json)
