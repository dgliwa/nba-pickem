#!/usr/bin/env python3
"""NBA Pick'em - Model Training Script

Trains the selected model (logistic regression on the pre-game Elo difference) and saves
it to worker/best_model.pkl. Reports a hold-out score on the latest training season
using a model fit only on earlier seasons, then refits on all seasons.

Usage:
    nba-pickem-train                          # Train on 2016-2026 (2015 is Elo warm-up)
    nba-pickem-train --seasons 2022,2023,2024 # Train on specific seasons
"""
import argparse
import pickle

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from nba_pickem.config import PROJECT_ROOT
from nba_pickem.dataloader import get_games
from nba_pickem.features import MODEL_FEATURES, add_matchup_diffs


MODEL_DIR = PROJECT_ROOT / "worker"
MODEL_PATH = MODEL_DIR / "best_model.pkl"
FEATURE_SET = "elo_only"
MODEL_TYPE = "lr"


def build_model():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42))


def season_data(games, seasons: list[int]):
    df = games[games['season'].isin(seasons)]
    return df[MODEL_FEATURES], df['home_team_wins'].astype(int)


def main():
    parser = argparse.ArgumentParser(description="Train NBA prediction model")
    parser.add_argument("--seasons", type=str, default=",".join(str(s) for s in range(2016, 2027)),
                        help="Comma-separated list of seasons to train on")
    args = parser.parse_args()

    seasons = sorted(int(s) for s in args.seasons.split(','))
    games = add_matchup_diffs(get_games(played_only=True))

    X_prior, y_prior = season_data(games, seasons[:-1])
    X_last, y_last = season_data(games, seasons[-1:])
    holdout_acc = build_model().fit(X_prior, y_prior).score(X_last, y_last)
    print(f"Hold-out {seasons[-1]} (trained on {seasons[:-1]}): {holdout_acc:.4f} on {len(X_last)} games")
    print(f"Always-home baseline: {y_last.mean():.4f}")

    X, y = season_data(games, seasons)
    model = build_model().fit(X, y)
    print(f"Fit final model on {len(X)} games from seasons {seasons}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump({
            'model': model,
            'feature_cols': MODEL_FEATURES,
            'model_type': MODEL_TYPE,
            'feature_set': FEATURE_SET,
            'train_seasons': seasons,
        }, f)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
