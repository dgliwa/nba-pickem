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


MODEL_PATH = PROJECT_ROOT / "worker" / "best_model.pkl"


FEATURE_COLS = [
    'home_team_enc', 'away_team_enc',
    'home_off_rtg_5', 'home_off_rtg_10',
    'home_def_rtg_5', 'home_def_rtg_10',
    'away_off_rtg_5', 'away_off_rtg_10',
    'away_def_rtg_5', 'away_def_rtg_10',
    'home_margin_5', 'home_margin_10',
    'away_margin_5', 'away_margin_10',
]


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
    return requests.get(url, headers=HEADERS).json()


def compute_team_features(team_id: int, prior_games: pd.DataFrame, n_values: list[int] = [5, 10]) -> dict:
    """Compute offensive/defensive ratings and margins for a team based on prior games."""
    team_prior = prior_games[
        (prior_games['home_team_id'] == team_id) | (prior_games['away_team_id'] == team_id)
    ].sort_values('game_date_est')
    
    features = {}
    
    for n in n_values:
        last_n = team_prior.tail(n)
        if last_n.empty:
            features[f'home_off_rtg_{n}'] = 100.0
            features[f'home_def_rtg_{n}'] = 100.0
            features[f'home_margin_{n}'] = 0.0
            features[f'away_off_rtg_{n}'] = 100.0
            features[f'away_def_rtg_{n}'] = 100.0
            features[f'away_margin_{n}'] = 0.0
            continue
        
        last_n = last_n.copy()
        last_n['is_home'] = last_n['home_team_id'] == team_id
        
        last_n['pts_for'] = last_n.apply(
            lambda r: r['home_team_points'] if r['home_team_id'] == team_id else r['away_team_points'], axis=1
        )
        last_n['pts_against'] = last_n.apply(
            lambda r: r['away_team_points'] if r['home_team_id'] == team_id else r['home_team_points'], axis=1
        )
        last_n['margin'] = last_n['pts_for'] - last_n['pts_against']
        
        if last_n['is_home'].any():
            home_games = last_n[last_n['is_home']]
            if not home_games.empty:
                features[f'home_off_rtg_{n}'] = home_games['pts_for'].mean()
                features[f'home_def_rtg_{n}'] = home_games['pts_against'].mean()
                features[f'home_margin_{n}'] = home_games['margin'].mean()
            else:
                features[f'home_off_rtg_{n}'] = 100.0
                features[f'home_def_rtg_{n}'] = 100.0
                features[f'home_margin_{n}'] = 0.0
        else:
            features[f'home_off_rtg_{n}'] = 100.0
            features[f'home_def_rtg_{n}'] = 100.0
            features[f'home_margin_{n}'] = 0.0
        
        if (~last_n['is_home']).any():
            away_games = last_n[~last_n['is_home']]
            if not away_games.empty:
                features[f'away_off_rtg_{n}'] = away_games['pts_for'].mean()
                features[f'away_def_rtg_{n}'] = away_games['pts_against'].mean()
                features[f'away_margin_{n}'] = away_games['margin'].mean()
            else:
                features[f'away_off_rtg_{n}'] = 100.0
                features[f'away_def_rtg_{n}'] = 100.0
                features[f'away_margin_{n}'] = 0.0
        else:
            features[f'away_off_rtg_{n}'] = 100.0
            features[f'away_def_rtg_{n}'] = 100.0
            features[f'away_margin_{n}'] = 0.0
    
    return features


def extract_game_features(games_response, previous_games, prediction_date: date, cat_mapping: dict):
    results = games_response['resultSets']
    game_headers = results[0]
    
    games = []
    for game in game_headers.get('rowSet'):
        game_id = game[2]
        home_team_id = game[6]
        away_team_id = game[7]
        
        home_features = compute_team_features(home_team_id, previous_games)
        away_features = compute_team_features(away_team_id, previous_games)
        
        games.append({
            "game_id": game_id,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "game_date_est": prediction_date,
            "home_team_enc": cat_mapping.get(home_team_id, -1),
            "away_team_enc": cat_mapping.get(away_team_id, -1),
            **home_features,
            **away_features,
        })
    
    return pd.DataFrame(games)


def predict_games(games_df, model):
    X = games_df[FEATURE_COLS].copy()
    games_df["predicted_home_team_wins"] = model.predict(X)
    return games_df


def main():
    parser = argparse.ArgumentParser(description="Generate NBA game predictions")
    parser.add_argument("date", nargs="?", help="Date to predict (YYYY-MM-DD)")
    args = parser.parse_args()

    prediction_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.now(ZoneInfo('US/Eastern')).date()

    print(f"Generating predictions for {prediction_date}...")

    model_data = load_model()
    model = model_data['model']
    
    previous_games = get_games(end_date=prediction_date.strftime('%Y-%m-%d'))
    
    cat_type = previous_games['home_team_id'].astype('category')
    cat_mapping = dict(zip(cat_type.cat.categories, cat_type.cat.codes))
    
    games_response = fetch_todays_games(prediction_date)

    games_df = extract_game_features(games_response, previous_games, prediction_date, cat_mapping)

    if games_df.empty:
        print("No games found for this date.")
        return

    predictions_df = predict_games(games_df, model)
    save_predictions(predictions_df)

    print(f"Saved {len(predictions_df)} predictions to database.")
    print("\nPredictions:")
    for _, row in predictions_df.iterrows():
        result = "HOME WIN" if row['predicted_home_team_wins'] else "AWAY WIN"
        print(f"  {row['home_team_id']} vs {row['away_team_id']}: {result}")


if __name__ == "__main__":
    main()