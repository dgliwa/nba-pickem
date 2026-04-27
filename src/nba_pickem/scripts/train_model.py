#!/usr/bin/env python3
"""NBA Pick'em - Model Training Script

Trains a model on historical NBA games and saves to pickle.

Usage:
    nba-pickem-train                           # Train classifier on 2022-2025
    nba-pickem-train --model regressor           # Train regressor (predicts margin)
    nba-pickem-train --model both              # Train both, compare results
"""
import argparse
import pickle
import pandas as pd
import numpy as np

from nba_pickem.config import PROJECT_ROOT
from nba_pickem.dataloader import get_games


MODEL_DIR = PROJECT_ROOT / "worker"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def prepare_training_data(games_df: pd.DataFrame, train_seasons: list[int], for_regressor: bool = False) -> tuple:
    df = games_df[games_df['season'].isin(train_seasons)].copy()
    df = df.dropna(subset=['home_win_pct_5', 'away_win_pct_5', 'off_rtg_5', 'def_rtg_5'])
    
    df['home_team_enc'] = df['home_team_id'].astype('category').cat.codes
    df['away_team_enc'] = df['away_team_id'].astype('category').cat.codes
    
    feature_cols = [
        'home_team_enc', 'away_team_enc',
        'home_win_pct_5', 'home_win_pct_10',
        'away_win_pct_5', 'away_win_pct_10',
        'off_rtg_5', 'off_rtg_10',
        'def_rtg_5', 'def_rtg_10',
        'margin_5', 'margin_10',
        'rest_days',
        'home_wpct_home', 'away_wpct_away',
    ]
    X = df[feature_cols].copy()
    
    if for_regressor:
        # For regressor: predict point margin (home_pts - away_pts)
        y = df['home_team_points'] - df['away_team_points']
    else:
        # For classifier: home wins?
        y = df['home_team_wins'].astype(int)
    
    return X, y


def train_classifier(X: pd.DataFrame, y: pd.Series) -> tuple:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(max_depth=7, n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    
    print(f"Classifier - Train accuracy: {train_acc:.4f}, Test accuracy: {test_acc:.4f}")
    
    model.fit(X, y)
    return model, test_acc


def train_regressor(X: pd.DataFrame, y: pd.Series) -> tuple:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, root_mean_squared_error
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(max_depth=7, n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    train_mae = mean_absolute_error(y_train, model.predict(X_train))
    test_mae = mean_absolute_error(y_test, model.predict(X_test))
    test_rmse = root_mean_squared_error(y_test, model.predict(X_test))
    
    print(f"Regressor - Train MAE: {train_mae:.2f}, Test MAE: {test_mae:.2f}, RMSE: {test_rmse:.2f}")
    
    # Convert to binary accuracy (margin > 0 = home wins)
    y_pred_binary = (model.predict(X_test) > 0).astype(int)
    y_test_binary = (y_test > 0).astype(int)
    accuracy = (y_pred_binary == y_test_binary).mean()
    print(f"Regressor -> Binary accuracy: {accuracy:.4f}")
    
    model.fit(X, y)
    return model, accuracy


def evaluate_on_season(model, X, y_true, season_name: str):
    if hasattr(model, 'predict'):
        y_pred = model.predict(X)
    
    if isinstance(y_pred[0], (int, np.integer)) or len(y_pred.shape) == 1:
        # Classifier
        accuracy = (y_pred == y_true).mean()
        print(f"{season_name} accuracy: {accuracy:.4f}")
        return accuracy
    else:
        # Regressor - convert to binary
        y_pred_binary = (y_pred > 0).astype(int)
        y_true_binary = (y_true > 0).astype(int)
        accuracy = (y_pred_binary == y_true_binary).mean()
        print(f"{season_name} accuracy: {accuracy:.4f}")
        return accuracy


def main():
    parser = argparse.ArgumentParser(description="Train NBA prediction model")
    parser.add_argument("--seasons", type=str, default="2022,2023,2024,2025",
                       help="Comma-separated list of seasons to train on")
    parser.add_argument("--model", type=str, default="classifier", choices=["classifier", "regressor", "both"],
                       help="Model type to train")
    args = parser.parse_args()
    
    train_seasons = [int(s) for s in args.seasons.split(',')]
    print(f"Training on seasons: {train_seasons}")
    
    games = get_games()
    print(f"Loaded {len(games)} games from database")
    
    X, y = prepare_training_data(games, train_seasons, for_regressor=(args.model == "regressor"))
    print(f"Prepared {len(X)} training samples")
    
    if args.model == "classifier":
        model, test_acc = train_classifier(X, y)
        with open(MODEL_DIR / "nba_model_classifier.pkl", 'wb') as f:
            pickle.dump(model, f)
        print(f"Saved classifier to {MODEL_DIR / 'nba_model_classifier.pkl'}")
        
    elif args.model == "regressor":
        model, accuracy = train_regressor(X, y)
        with open(MODEL_DIR / "nba_model_regressor.pkl", 'wb') as f:
            pickle.dump(model, f)
        print(f"Saved regressor to {MODEL_DIR / 'nba_model_regressor.pkl'}")
        
    elif args.model == "both":
        print("\n=== Training Classifier ===")
        X_clf, y_clf = prepare_training_data(games, train_seasons, for_regressor=False)
        clf_model, clf_test_acc = train_classifier(X_clf, y_clf)
        
        print("\n=== Training Regressor ===")
        X_reg, y_reg = prepare_training_data(games, train_seasons, for_regressor=True)
        reg_model, reg_accuracy_orig = train_regressor(X_reg, y_reg)
        
        # Evaluate on 2026 - need to use same category encoding
        print("\n=== Evaluating on 2026 (held-out) ===")
        
        df_train = games[games['season'].isin(train_seasons)].copy()
        df_train = df_train.dropna(subset=['home_win_pct_5'])
        cat_type = df_train['home_team_id'].astype('category')
        cat_mapping = dict(zip(cat_type.cat.categories, cat_type.cat.codes))
        
        test_2026 = games[games['season'] == 2026].copy()
        test_2026 = test_2026.dropna(subset=['home_win_pct_5'])
        
        test_2026['home_team_enc'] = test_2026['home_team_id'].map(cat_mapping).fillna(-1)
        test_2026['away_team_enc'] = test_2026['away_team_id'].map(cat_mapping).fillna(-1)
        
        feature_cols = [
            'home_team_enc', 'away_team_enc',
            'home_win_pct_5', 'home_win_pct_10',
            'away_win_pct_5', 'away_win_pct_10',
            'off_rtg_5', 'off_rtg_10',
            'def_rtg_5', 'def_rtg_10',
            'margin_5', 'margin_10',
            'rest_days',
            'home_wpct_home', 'away_wpct_away',
        ]
        X_2026 = test_2026[feature_cols]
        
        # Classifier evaluation
        y_2026_clf = test_2026['home_team_wins'].astype(int)
        clf_acc = (clf_model.predict(X_2026) == y_2026_clf).mean()
        print(f"Classifier 2026 accuracy: {clf_acc:.4f}")
        
        # Regressor evaluation  
        y_2026_reg = test_2026['home_team_points'] - test_2026['away_team_points']
        reg_preds = reg_model.predict(X_2026)
        reg_acc = ((reg_preds > 0).astype(int) == (y_2026_reg > 0).astype(int)).mean()
        print(f"Regressor 2026 accuracy: {reg_acc:.4f}")
        
        print(f"\n=== Summary ===")
        print(f"2026 - Classifier: {clf_acc:.4f}")
        print(f"2026 - Regressor: {reg_acc:.4f}")
        
        if clf_acc >= reg_acc:
            print(f"Recommendation: Use CLASSIFIER ({clf_acc:.1%} vs {reg_acc:.1%})")
            with open(MODEL_DIR / "nba_model.pkl", 'wb') as f:
                pickle.dump(clf_model, f)
            with open(MODEL_DIR / "nba_model_classifier.pkl", 'wb') as f:
                pickle.dump(clf_model, f)
        else:
            print(f"Recommendation: Use REGRESSOR ({reg_acc:.1%} vs {clf_acc:.1%})")
            with open(MODEL_DIR / "nba_model.pkl", 'wb') as f:
                pickle.dump(reg_model, f)
            with open(MODEL_DIR / "nba_model_regressor.pkl", 'wb') as f:
                pickle.dump(reg_model, f)


if __name__ == "__main__":
    main()