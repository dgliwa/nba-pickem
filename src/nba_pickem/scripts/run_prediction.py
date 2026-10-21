#!/usr/bin/env python3
"""NBA Pick'em - Prediction Script

Predicts a day's unplayed games (from the games table) using the trained model.

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
from nba_pickem.dataloader import get_games, get_unplayed_games, save_predictions
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


def predict_for_date(prediction_date: date) -> pd.DataFrame:
    """Predict and save unplayed games on a date. Played games are never re-predicted."""
    schedule = get_unplayed_games(prediction_date.isoformat())
    if schedule.empty:
        return schedule
    previous_games = get_games(end_date=prediction_date.isoformat(), played_only=True)
    predictions = predict_games(attach_features(schedule, previous_games, prediction_date), load_model())
    save_predictions(predictions)
    return predictions


def print_predictions(predictions: pd.DataFrame):
    for _, row in predictions.iterrows():
        winner = row['home_team_id'] if row['predicted_home_team_wins'] else row['away_team_id']
        print(f"  {row['home_team_id']} vs {row['away_team_id']}: {winner} ({row['home_win_probability']:.0%} home)")


def main():
    parser = argparse.ArgumentParser(description="Generate NBA game predictions")
    parser.add_argument("date", nargs="?", help="Date to predict (YYYY-MM-DD)")
    args = parser.parse_args()

    prediction_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(ZoneInfo('US/Eastern')).date()

    print(f"Generating predictions for {prediction_date}...")
    predictions = predict_for_date(prediction_date)

    if predictions.empty:
        print("No unplayed games stored for this date. Run nba-pickem-daily or nba-pickem-load-bball-ref --season N first.")
        return

    print(f"Saved {len(predictions)} predictions to database.")
    print_predictions(predictions)


if __name__ == "__main__":
    main()
