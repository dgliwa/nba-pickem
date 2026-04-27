#!/usr/bin/env python3
"""NBA Pick'em - Prediction Script

Generates predictions for today's games using the trained model.

Usage:
    nba-pickem-predict              # Predict today's games
    nba-pickem-predict 2024-01-15   # Predict specific date
"""
import argparse
import pickle
import pandas as pd
import numpy as np
import requests
from datetime import datetime, date
from zoneinfo import ZoneInfo

from nba_pickem.config import PROJECT_ROOT
from nba_pickem.dataloader import get_games, save_predictions


MODEL_PATH = PROJECT_ROOT / "worker" / "nba_model.pkl"


def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def fetch_todays_games(prediction_date: date):
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
    formatted_date = prediction_date.strftime('%m/%d/%Y')
    url = f"https://stats.nba.com/stats/scoreboardV2?DayOffset=0&LeagueID=00&gameDate={formatted_date}"
    return requests.get(url, headers=HEADERS).json()


def extract_game_features(games_response, previous_games, prediction_date: date):
    results = games_response['resultSets']
    game_headers = results[0]
    eastern_standings = results[4]
    western_standings = results[5]

    games = []
    for game in game_headers.get('rowSet'):
        game_id = game[2]
        home_team_id = game[6]
        away_team_id = game[7]

        home_team_rank = _get_team_rank(home_team_id, eastern_standings, western_standings)
        away_team_rank = _get_team_rank(away_team_id, eastern_standings, western_standings)

        home_win_pct = home_team_rank[9]
        home_home_wins, home_home_losses = home_team_rank[10].split("-")
        home_home_win_pct = int(home_home_wins) / (int(home_home_wins) + int(home_home_losses)) if int(home_home_wins) + int(home_home_losses) > 0 else 0

        away_win_pct = away_team_rank[9]
        away_away_wins, away_away_losses = away_team_rank[11].split("-")
        away_away_win_pct = int(away_away_wins) / (int(away_away_wins) + int(away_away_losses)) if int(away_away_wins) + int(away_away_losses) > 0 else 0

        game_date = datetime.strptime(game[0], "%Y-%m-%dT%H:%M:%S")
        yesterday = game_date - pd.Timedelta(days=1)

        home_b2b = len(previous_games[(previous_games['game_date_est'].dt.date == yesterday.date()) & (
            (previous_games['home_team_id'] == home_team_id) | (previous_games["away_team_id"] == home_team_id))]) > 0

        away_b2b = len(previous_games[(previous_games['game_date_est'].dt.date == yesterday.date()) & (
            (previous_games['home_team_id'] == away_team_id) | (previous_games["away_team_id"] == away_team_id))]) > 0

        games.append({
            "game_id": game_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "game_date_est": prediction_date,
            "home_win_pct": home_win_pct,
            "home_home_win_pct": home_home_win_pct,
            "away_win_pct": away_win_pct,
            "away_away_win_pct": away_away_win_pct,
            "home_team_b2b": home_b2b,
            "away_team_b2b": away_b2b,
            "home_last_10_win_pct": _get_last_n_win_pct(home_team_id, 10, previous_games),
            "away_last_10_win_pct": _get_last_n_win_pct(away_team_id, 10, previous_games),
        })
    return pd.DataFrame(games)


def _get_team_rank(team_id, eastern, western):
    for team in eastern.get("rowSet"):
        if team[0] == team_id:
            return team
    for team in western.get("rowSet"):
        if team[0] == team_id:
            return team
    return None


def _get_last_n_win_pct(team_id, n, games):
    team_games = games[(games['home_team_id'] == team_id) | (games['away_team_id'] == team_id)]
    team_games = team_games.sort_values('game_date_est')
    team_games['is_home'] = team_games['home_team_id'] == team_id
    team_games['win'] = team_games['is_home'] == team_games['home_team_wins']
    return team_games['win'].tail(n).mean()


def predict_games(games_df, model):
    feature_cols = [
        "home_team_id",
        "away_team_id",
        "home_win_pct",
        "home_home_win_pct",
        "away_win_pct",
        "away_away_win_pct",
        "home_team_b2b",
        "away_team_b2b",
        "home_last_10_win_pct",
        "away_last_10_win_pct",
    ]
    X = games_df[feature_cols].copy()
    X["home_team_b2b"] = X["home_team_b2b"].astype(int)
    X["away_team_b2b"] = X["away_team_b2b"].astype(int)
    games_df["predicted_home_team_wins"] = model.predict(X)
    return games_df


def main():
    parser = argparse.ArgumentParser(description="Generate NBA game predictions")
    parser.add_argument("date", nargs="?", help="Date to predict (YYYY-MM-DD)")
    args = parser.parse_args()

    prediction_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(ZoneInfo('US/Eastern')).date()

    print(f"Generating predictions for {prediction_date}...")

    model = load_model()
    previous_games = get_games(end_date=prediction_date.strftime('%Y-%m-%d'))
    games_response = fetch_todays_games(prediction_date)

    games_df = extract_game_features(games_response, previous_games, prediction_date)

    if games_df.empty:
        print("No games found for this date.")
        return

    predictions_df = predict_games(games_df, model)
    save_predictions(predictions_df)

    print(f"Saved {len(predictions_df)} predictions to database.")


if __name__ == "__main__":
    main()