#!/usr/bin/env python3
"""Model experimentation script to find best model + feature combination."""
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler

from nba_pickem.config import PROJECT_ROOT
from nba_pickem.dataloader import get_games


MODEL_DIR = PROJECT_ROOT / "worker"


FEATURE_SETS = {
    "all_features": [
        'home_team_enc', 'away_team_enc',
        'home_win_pct_5', 'home_win_pct_10',
        'away_win_pct_5', 'away_win_pct_10',
        'home_off_rtg_5', 'home_off_rtg_10',
        'home_def_rtg_5', 'home_def_rtg_10',
        'home_margin_5', 'home_margin_10',
        'away_off_rtg_5', 'away_off_rtg_10',
        'away_def_rtg_5', 'away_def_rtg_10',
        'away_margin_5', 'away_margin_10',
        'rest_days',
        'home_wpct_home', 'away_wpct_away',
    ],
    "home_only": [
        'home_team_enc', 'away_team_enc',
        'home_win_pct_5', 'home_win_pct_10',
        'home_off_rtg_5', 'home_off_rtg_10',
        'home_def_rtg_5', 'home_def_rtg_10',
        'home_margin_5', 'home_margin_10',
        'rest_days',
        'home_wpct_home',
    ],
    "away_only": [
        'home_team_enc', 'away_team_enc',
        'away_win_pct_5', 'away_win_pct_10',
        'away_off_rtg_5', 'away_off_rtg_10',
        'away_def_rtg_5', 'away_def_rtg_10',
        'away_margin_5', 'away_margin_10',
        'away_wpct_away',
    ],
    "differentials": [
        'home_team_enc', 'away_team_enc',
        'home_win_pct_5', 'away_win_pct_5',
        'home_off_rtg_5', 'away_off_rtg_5',
        'home_def_rtg_5', 'away_def_rtg_5',
        'home_margin_5', 'away_margin_5',
        'rest_days',
    ],
    "ratings_only": [
        'home_team_enc', 'away_team_enc',
        'home_off_rtg_5', 'home_off_rtg_10',
        'home_def_rtg_5', 'home_def_rtg_10',
        'away_off_rtg_5', 'away_off_rtg_10',
        'away_def_rtg_5', 'away_def_rtg_10',
        'home_margin_5', 'home_margin_10',
        'away_margin_5', 'away_margin_10',
    ],
    "ratings_plus_rest": [
        'home_team_enc', 'away_team_enc',
        'home_off_rtg_5', 'home_off_rtg_10',
        'home_def_rtg_5', 'home_def_rtg_10',
        'away_off_rtg_5', 'away_off_rtg_10',
        'away_def_rtg_5', 'away_def_rtg_10',
        'home_margin_5', 'home_margin_10',
        'away_margin_5', 'away_margin_10',
        'rest_days',
    ],
    "winpct_only": [
        'home_team_enc', 'away_team_enc',
        'home_win_pct_5', 'home_win_pct_10',
        'away_win_pct_5', 'away_win_pct_10',
        'home_wpct_home', 'away_wpct_away',
    ],
    "top_10": [
        'home_team_enc', 'away_team_enc',
        'home_win_pct_5',
        'away_win_pct_5',
        'home_off_rtg_5',
        'away_off_rtg_5',
        'home_def_rtg_5',
        'away_def_rtg_5',
        'home_margin_5',
        'away_margin_5',
    ],
}


MODELS = {
    "rf_shallow": lambda: RandomForestClassifier(max_depth=5, n_estimators=100, random_state=42, n_jobs=-1),
    "rf_medium": lambda: RandomForestClassifier(max_depth=7, n_estimators=150, random_state=42, n_jobs=-1),
    "rf_deep": lambda: RandomForestClassifier(max_depth=10, n_estimators=200, random_state=42, n_jobs=-1),
    "gb": lambda: GradientBoostingClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42),
    "lr": lambda: LogisticRegression(max_iter=1000, random_state=42),
}


def prepare_data(games_df: pd.DataFrame, train_seasons: list[int], feature_cols: list[str]) -> tuple:
    df = games_df[games_df['season'].isin(train_seasons)].copy()
    
    df['home_team_enc'] = df['home_team_id'].astype('category').cat.codes
    df['away_team_enc'] = df['away_team_id'].astype('category').cat.codes
    
    base_cols = [c for c in feature_cols if c not in ['home_team_enc', 'away_team_enc']]
    df = df.dropna(subset=base_cols)
    
    X = df[feature_cols].copy()
    y = df['home_team_wins'].astype(int)
    
    return X, y


def evaluate_model(model_fn, X_train, X_test, y_train, y_test):
    model = model_fn()
    model.fit(X_train, y_train)
    
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    
    return model, train_acc, test_acc


def run_experiment():
    games = get_games()
    train_seasons = [2022, 2023, 2024, 2025]
    
    results = []
    
    for feat_name, feat_cols in FEATURE_SETS.items():
        print(f"\n{'='*60}")
        print(f"Feature Set: {feat_name} ({len(feat_cols)} features)")
        print('='*60)
        
        X, y = prepare_data(games, train_seasons, feat_cols)
        print(f"Training samples: {len(X)}")
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        for model_name, model_fn in MODELS.items():
            if model_name == "lr":
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
                model = model_fn()
                model.fit(X_train_scaled, y_train)
                train_acc = model.score(X_train_scaled, y_train)
                test_acc = model.score(X_test_scaled, y_test)
                model.scaler = scaler
            else:
                model, train_acc, test_acc = evaluate_model(model_fn, X_train, X_test, y_train, y_test)
            
            results.append({
                'feature_set': feat_name,
                'model': model_name,
                'train_acc': train_acc,
                'test_acc': test_acc,
                'n_features': len(feat_cols),
                'model_obj': model,
                'feature_cols': feat_cols,
            })
            
            print(f"  {model_name:15} | Train: {train_acc:.4f} | Test: {test_acc:.4f}")
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('test_acc', ascending=False)
    
    print(f"\n\n{'='*60}")
    print("TOP 10 CONFIGURATIONS (by test accuracy)")
    print('='*60)
    print(results_df[['feature_set', 'model', 'train_acc', 'test_acc', 'n_features']].head(10).to_string(index=False))
    
    best = results_df.iloc[0]
    print(f"\n\nBest: {best['feature_set']} + {best['model']} = {best['test_acc']:.4f}")
    
    print("\n\n=== Evaluating best models on 2026 (held-out) ===")
    
    df_train = games[games['season'].isin(train_seasons)].copy()
    cat_type = df_train['home_team_id'].astype('category')
    cat_mapping = dict(zip(cat_type.cat.categories, cat_type.cat.codes))
    
    test_2026 = games[games['season'] == 2026].copy()
    
    top_results = []
    for i, row in results_df.head(5).iterrows():
        feat_cols = row['feature_cols']
        base_cols = [c for c in feat_cols if c not in ['home_team_enc', 'away_team_enc']]
        test_df = test_2026.dropna(subset=base_cols).copy()
        
        test_df['home_team_enc'] = test_df['home_team_id'].map(cat_mapping).fillna(-1)
        test_df['away_team_enc'] = test_df['away_team_id'].map(cat_mapping).fillna(-1)
        
        X_2026 = test_df[feat_cols]
        y_2026 = test_df['home_team_wins'].astype(int)
        
        model = row['model_obj']
        
        if row['model'] == 'lr':
            X_2026 = model.scaler.transform(X_2026)
        
        y_pred = model.predict(X_2026)
        acc_2026 = (y_pred == y_2026).mean()
        
        top_results.append({
            'feature_set': row['feature_set'],
            'model': row['model'],
            'test_acc': row['test_acc'],
            '2026_acc': acc_2026,
        })
        
        print(f"  {row['feature_set']:20} + {row['model']:15} | Val: {row['test_acc']:.4f} | 2026: {acc_2026:.4f}")
    
    final_df = pd.DataFrame(top_results).sort_values('2026_acc', ascending=False)
    print(f"\n=== BEST ON 2026: {final_df.iloc[0]['feature_set']} + {final_df.iloc[0]['model']} = {final_df.iloc[0]['2026_acc']:.4f} ===")
    
    best_row = final_df.iloc[0]
    best_model_row = results_df[(results_df['feature_set'] == best_row['feature_set']) & (results_df['model'] == best_row['model'])].iloc[0]
    
    with open(MODEL_DIR / "best_model.pkl", 'wb') as f:
        pickle.dump({
            'model': best_model_row['model_obj'],
            'feature_cols': best_model_row['feature_cols'],
            'model_type': best_row['model'],
            'feature_set': best_row['feature_set'],
        }, f)
    
    print(f"\nSaved best model to {MODEL_DIR / 'best_model.pkl'}")
    
    return final_df


if __name__ == "__main__":
    run_experiment()