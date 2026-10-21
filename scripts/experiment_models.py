#!/usr/bin/env python3
"""Walk-forward model experimentation.

Selection uses only temporal folds (train on earlier seasons, test on the next).
The final season is touched once, for the selected config and fixed references.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from nba_pickem.dataloader import get_games
from nba_pickem.features import add_matchup_diffs


SELECTION_FOLDS = [(2024, [2022, 2023]), (2025, [2022, 2023, 2024])]
FINAL_FOLD = (2026, [2022, 2023, 2024, 2025])
CLAIMED_WINNER = ("ratings_only", "rf_shallow")

TEAMS = ['home_team_enc', 'away_team_enc']
OFF_DEF = [f'{side}_{kind}_rtg_{n}' for side in ('home', 'away') for kind in ('off', 'def') for n in (5, 10)]
MARGIN = [f'{side}_margin_{n}' for side in ('home', 'away') for n in (5, 10)]
WINPCT = [f'{side}_win_pct_{n}' for side in ('home', 'away') for n in (5, 10)]
DIFFS = ['d_margin_5', 'd_margin_10', 'd_win_pct_5', 'd_win_pct_10']

FEATURE_SETS = {
    "all_features": TEAMS + WINPCT + OFF_DEF + MARGIN + ['rest_days', 'home_wpct_home', 'away_wpct_away'],
    "ratings_only": TEAMS + OFF_DEF + MARGIN,
    "ratings_no_margin": TEAMS + OFF_DEF,
    "ratings_no_team": OFF_DEF + MARGIN,
    "ratings_no_margin_no_team": OFF_DEF,
    "ratings_plus_rest": TEAMS + OFF_DEF + MARGIN + ['rest_days'],
    "winpct_only": TEAMS + WINPCT + ['home_wpct_home', 'away_wpct_away'],
    "diffs_only": DIFFS,
    "diffs_plus_home_away": DIFFS + ['home_wpct_home', 'away_wpct_away'],
}

MODELS = {
    "rf_shallow": lambda: RandomForestClassifier(max_depth=5, n_estimators=100, random_state=42, n_jobs=-1),
    "rf_medium": lambda: RandomForestClassifier(max_depth=7, n_estimators=150, random_state=42, n_jobs=-1),
    "rf_deep": lambda: RandomForestClassifier(max_depth=10, n_estimators=200, random_state=42, n_jobs=-1),
    "gb": lambda: GradientBoostingClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42),
    "lr": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42)),
}


def split_fold(games: pd.DataFrame, test_season: int, train_seasons: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = games[games['season'].isin(train_seasons)].copy()
    test = games[games['season'] == test_season].copy()
    team_codes = {team: code for code, team in enumerate(sorted(train['home_team_id'].unique()))}
    for df in (train, test):
        df['home_team_enc'] = df['home_team_id'].map(team_codes).fillna(-1)
        df['away_team_enc'] = df['away_team_id'].map(team_codes).fillna(-1)
    return train, test


def fit_and_score(model_name: str, columns: list[str], train: pd.DataFrame, test: pd.DataFrame) -> tuple[int, int]:
    model = MODELS[model_name]()
    model.fit(train[columns], train['home_team_wins'].astype(int))
    correct = int((model.predict(test[columns]) == test['home_team_wins'].astype(int)).sum())
    return correct, len(test)


def run_selection(games: pd.DataFrame) -> pd.DataFrame:
    folds = {season: split_fold(games, season, train_seasons) for season, train_seasons in SELECTION_FOLDS}
    rows = []
    for feature_set, columns in FEATURE_SETS.items():
        for model_name in MODELS:
            scores = {season: fit_and_score(model_name, columns, *folds[season]) for season in folds}
            total_correct = sum(c for c, _ in scores.values())
            total_n = sum(n for _, n in scores.values())
            rows.append({
                'feature_set': feature_set,
                'model': model_name,
                'n_features': len(columns),
                **{f'acc_{season}': c / n for season, (c, n) in scores.items()},
                'acc_mean': total_correct / total_n,
                'se': np.sqrt(total_correct / total_n * (1 - total_correct / total_n) / total_n),
            })
    return pd.DataFrame(rows).sort_values('acc_mean', ascending=False).reset_index(drop=True)


def report_final(games: pd.DataFrame, selected: tuple[str, str]) -> None:
    season, train_seasons = FINAL_FOLD
    train, test = split_fold(games, season, train_seasons)
    home_rate = test['home_team_wins'].astype(int).mean()
    print(f"\n=== FINAL {season} (single look, {len(test)} games) ===")
    print(f"always-home baseline: {home_rate:.4f}")
    for label, (feature_set, model_name) in {"selected": selected, "previously claimed winner": CLAIMED_WINNER}.items():
        correct, n = fit_and_score(model_name, FEATURE_SETS[feature_set], train, test)
        acc = correct / n
        se = np.sqrt(acc * (1 - acc) / n)
        print(f"{label:28} {feature_set} + {model_name}: {acc:.4f} +/- {se:.4f} ({correct}/{n})")


def main():
    games = add_matchup_diffs(get_games())
    results = run_selection(games)

    print("=== WALK-FORWARD SELECTION (folds: 2024<-2022-23, 2025<-2022-24) ===")
    for season, _ in SELECTION_FOLDS:
        home_rate = games[games['season'] == season]['home_team_wins'].astype(int).mean()
        print(f"always-home baseline {season}: {home_rate:.4f}")
    print(results.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    best = results.iloc[0]
    report_final(games, (best['feature_set'], best['model']))


if __name__ == "__main__":
    main()
