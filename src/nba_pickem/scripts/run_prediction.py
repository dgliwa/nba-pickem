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

from nba_pickem.config import PROJECT_ROOT
from nba_pickem.dataloader import get_games, save_predictions
from nba_pickem.schedule import fetch_scoreboard, parse_scoreboard
from nba_pickem.features import add_matchup_diffs, matchup_features, season_for_date


MODEL_PATH = PROJECT_ROOT / "worker" / "best_model.pkl"


def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def attach_features(schedule: pd.DataFrame, previous_games: pd.DataFrame, prediction_date: date) -> pd.DataFrame:
    game_date = pd.Timestamp(prediction_date)
    prior = previous_games[
        (previous_games['game_date_est'] < game_date)
        & (previous_games['season'] == season_for_date(game_date))
    ]
    features = [matchup_features(prior, g.home_team_id, g.away_team_id) for g in schedule.itertuples()]
    return add_matchup_diffs(pd.concat([schedule.reset_index(drop=True), pd.DataFrame(features)], axis=1))


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

    schedule = parse_scoreboard(fetch_scoreboard(prediction_date), prediction_date)
    games_df = attach_features(schedule, previous_games, prediction_date)

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
