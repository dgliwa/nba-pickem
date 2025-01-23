import json
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from dao import (
    retrieve_game_predictions_df,
    retrieve_teams_df,
    redis_client,
    retrieve_game_predictions_with_results
)
from worker import collect_game_data


def predictions_for_date(game_date=datetime.now(ZoneInfo('US/Eastern')).date(), bet_amount=10.0):
    # games_str = redis_client.get(f"{game_date.strftime('%Y-%m-%d')}_games")
    # if games_str:
    #     return json.loads(games_str)

    teams = retrieve_teams_df()
    predictions = retrieve_game_predictions_df(game_date)

    predictions_for_date = predictions[predictions["GAME_DATE_EST"] == np.datetime64(game_date)]
    if predictions_for_date.empty:
        collect_game_data.delay()
        return []

    formatted_predictions = _combine_team_data_with_predictions(teams, predictions_for_date, bet_amount)
    _cache_predictions(formatted_predictions, game_date)
    return formatted_predictions.to_dict(orient='records')


def get_historical_accuracy(bet_amount=10.0):
    return retrieve_game_predictions_with_results(bet_amount)


def _combine_team_data_with_predictions(teams, game_predictions, bet_amount):
    game_predictions = game_predictions.merge(teams, left_on="HOME_TEAM_ID", right_on="TEAM_ID")
    game_predictions = game_predictions.merge(teams, left_on="AWAY_TEAM_ID", right_on="TEAM_ID", suffixes=("_HOME", "_AWAY"))
    game_predictions.drop(columns=["TEAM_ID_HOME", "TEAM_ID_AWAY"], inplace=True)
    game_predictions["PREDICTED_WINNER"] = game_predictions.apply(lambda row: _prettify_winner(row, row["PREDICTED_HOME_TEAM_WINS"]), axis=1)
    game_predictions["ACTUAL_WINNER"] = game_predictions.apply(lambda row: _prettify_winner(row, row["HOME_TEAM_WINS"]), axis=1)
    game_predictions["CORRECT_PREDICTION"] = game_predictions.apply(_correct_prediction, axis=1)
    game_predictions["WIN_AGAINST_MONEYLINE"] = game_predictions.apply(_win_against_moneyline, axis=1)
    game_predictions["GAME_WINNINGS"] = game_predictions.apply(lambda row: _winnings(row, bet_amount), axis=1)
    game_predictions["GAME_DATE_EST"] = game_predictions["GAME_DATE_EST"].dt.strftime('%Y-%m-%d')
    return game_predictions[
        [
            "GAME_ID",
            "GAME_DATE_EST",
            "HOME_WIN_PCT",
            "HOME_HOME_WIN_PCT",
            "AWAY_WIN_PCT",
            "AWAY_AWAY_WIN_PCT",
            "HOME_TEAM_B2B",
            "AWAY_TEAM_B2B",
            "HOME_LAST_10_WIN_PCT",
            "AWAY_LAST_10_WIN_PCT",
            "ABBREVIATION_HOME",
            "NICKNAME_HOME",
            "ABBREVIATION_AWAY",
            "NICKNAME_AWAY",
            "PREDICTED_WINNER",
            "ACTUAL_WINNER",
            "CORRECT_PREDICTION",
            "HOME_ODDS",
            "AWAY_ODDS",
            "GAME_WINNINGS",
            "WIN_AGAINST_MONEYLINE"
        ]
    ]


def _prettify_winner(row, home_team_wins):
    if home_team_wins is None:
        return ""
    if home_team_wins == 1:
        return f"{row['ABBREVIATION_HOME']} {row['NICKNAME_HOME']}"
    else:
        return f"{row['ABBREVIATION_AWAY']} {row['NICKNAME_AWAY']}"


def _winnings(row, bet_amount):
    if row["HOME_TEAM_WINS"] is None:
        return pd.NA

    if row["CORRECT_PREDICTION"]:
        if row["HOME_TEAM_WINS"]:
            if not row["HOME_ODDS"]:
                return 0
            elif row["HOME_ODDS"] < 0:
                return bet_amount * (100.0 / abs(row["HOME_ODDS"]))
            else:
                return bet_amount * (row["HOME_ODDS"] / 100.0)
        else:
            if not row["AWAY_ODDS"]:
                return 0
            elif row["AWAY_ODDS"] < 0:
                return bet_amount * (100.0 / abs(row["AWAY_ODDS"]))
            else:
                return bet_amount * (row["AWAY_ODDS"] / 100.0)
    else:
        return -bet_amount


def _correct_prediction(row):
    return row["PREDICTED_HOME_TEAM_WINS"] == row["HOME_TEAM_WINS"]


def _win_against_moneyline(row):
    if row["HOME_TEAM_WINS"] is None:
        return None
    
    if (row["PREDICTED_HOME_TEAM_WINS"] and row["HOME_ODDS"] > 0) or (not row["PREDICTED_HOME_TEAM_WINS"] and row["AWAY_ODDS"] > 0):
        return row["CORRECT_PREDICTION"]
    return False


def _cache_predictions(games, game_date):
    todays_games_json = games.to_json(orient='records')
    redis_client.setex(f"{game_date.strftime('%Y-%m-%d')}_games", 3600, todays_games_json)
