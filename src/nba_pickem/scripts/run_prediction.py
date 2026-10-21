#!/usr/bin/env python3
"""NBA Pick'em - Prediction Script

Generates predictions for a day's games using the trained model.

Usage:
    nba-pickem-predict              # Predict today's games
    nba-pickem-predict 2024-01-15   # Predict specific date
"""
import argparse
import pickle
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from nba_pickem.config import PROJECT_ROOT
from nba_pickem.dataloader import get_games, save_predictions
from nba_pickem.features import add_matchup_diffs, matchup_features, season_for_date


MODEL_PATH = PROJECT_ROOT / "worker" / "best_model.pkl"
REQUEST_TIMEOUT_SECONDS = 20


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
        "User-Agent": "Mozilla/5.0 (X11; X86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    formatted_date = prediction_date.strftime('%m/%d/%Y')
    url = f"https://stats.nba.com/stats/scoreboardV2?DayOffset=0&LeagueID=00&gameDate={formatted_date}"
    return requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS).json()


def team_abbreviations(games_response) -> dict:
    # TODO: unverified against a live response (stats.nba.com timed out when this was written)
    line_scores = next(rs for rs in games_response['resultSets'] if rs['name'] == 'LineScore')
    id_col = line_scores['headers'].index('TEAM_ID')
    abbr_col = line_scores['headers'].index('TEAM_ABBREVIATION')
    return {row[id_col]: row[abbr_col] for row in line_scores['rowSet']}


def extract_game_features(games_response, previous_games: pd.DataFrame, prediction_date: date) -> pd.DataFrame:
    game_date = pd.Timestamp(prediction_date)
    prior = previous_games[
        (previous_games['game_date_est'] < game_date)
        & (previous_games['season'] == season_for_date(game_date))
    ]
    abbreviations = team_abbreviations(games_response)
    game_headers = next(rs for rs in games_response['resultSets'] if rs['name'] == 'GameHeader')

    games = []
    for game in game_headers['rowSet']:
        home_team, away_team = abbreviations[game[6]], abbreviations[game[7]]
        games.append({
            "game_id": game[2],
            "home_team_id": home_team,
            "away_team_id": away_team,
            "game_date_est": prediction_date,
            **matchup_features(prior, home_team, away_team),
        })

    return add_matchup_diffs(pd.DataFrame(games))


def predict_games(games_df: pd.DataFrame, model_data: dict) -> pd.DataFrame:
    X = games_df[model_data['feature_cols']]
    model = model_data['model']
    games_df["home_win_probability"] = model.predict_proba(X)[:, 1]
    games_df["predicted_home_team_wins"] = games_df["home_win_probability"] >= 0.5
    return games_df


def main():
    parser = argparse.ArgumentParser(description="Generate NBA game predictions")
    parser.add_argument("date", nargs="?", help="Date to predict (YYYY-MM-DD)")
    args = parser.parse_args()

    prediction_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(ZoneInfo('US/Eastern')).date()

    print(f"Generating predictions for {prediction_date}...")

    model_data = load_model()
    previous_games = get_games(end_date=prediction_date.strftime('%Y-%m-%d'))

    games_response = fetch_todays_games(prediction_date)
    games_df = extract_game_features(games_response, previous_games, prediction_date)

    if games_df.empty:
        print("No games found for this date.")
        return

    predictions_df = predict_games(games_df, model_data)
    save_predictions(predictions_df)

    print(f"Saved {len(predictions_df)} predictions to database.")
    print("\nPredictions:")
    for _, row in predictions_df.iterrows():
        winner = row['home_team_id'] if row['predicted_home_team_wins'] else row['away_team_id']
        print(f"  {row['home_team_id']} vs {row['away_team_id']}: {winner} ({row['home_win_probability']:.0%} home)")


if __name__ == "__main__":
    main()
