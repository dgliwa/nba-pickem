#!/usr/bin/env python3
"""NBA Pick'em - Model Training Script

Trains a RandomForest model on historical NBA games and saves to pickle.

Usage:
    nba-pickem-train
"""
import argparse
import pickle
import pandas as pd
import numpy as np

from nba_pickem.config import PROJECT_ROOT
from nba_pickem.dataloader import get_games


MODEL_PATH = PROJECT_ROOT / "worker" / "nba_model.pkl"


def prepare_training_data(games_df: pd.DataFrame, train_seasons: list[int]) -> tuple:
    df = games_df[games_df['season'].isin(train_seasons)].copy()
    df = df.dropna(subset=['home_last_10_win_pct', 'away_last_10_win_pct', 'home_team_wins'])
    
    df['home_team_enc'] = df['home_team_id'].astype('category').cat.codes
    df['away_team_enc'] = df['away_team_id'].astype('category').cat.codes
    
    feature_cols = [
        'home_team_enc', 'away_team_enc',
        'home_last_10_win_pct', 'away_last_10_win_pct',
        'home_team_b2b', 'away_team_b2b',
    ]
    X = df[feature_cols].copy()
    X['home_team_b2b'] = X['home_team_b2b'].astype(int)
    X['away_team_b2b'] = X['away_team_b2b'].astype(int)
    y = df['home_team_wins'].astype(int)
    
    return X, y


def train_model(X: pd.DataFrame, y: pd.Series) -> dict:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    model = RandomForestClassifier(
        max_depth=7,
        n_estimators=100,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    
    print(f"Train accuracy: {train_acc:.4f}")
    print(f"Test accuracy: {test_acc:.4f}")
    
    model.fit(X, y)
    return model


def main():
    parser = argparse.ArgumentParser(description="Train NBA prediction model")
    parser.add_argument("--seasons", type=str, default="2022,2023,2024,2025",
                      help="Comma-separated list of seasons to train on (default: 2022,2023,2024,2025)")
    args = parser.parse_args()
    
    train_seasons = [int(s) for s in args.seasons.split(',')]
    print(f"Training on seasons: {train_seasons}")
    
    games = get_games()
    print(f"Loaded {len(games)} games from database")
    
    X, y = prepare_training_data(games, train_seasons)
    print(f"Prepared {len(X)} training samples")
    
    model = train_model(X, y)
    
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()