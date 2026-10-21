"""Model feature definitions shared by training and prediction.

Selected via walk-forward evaluation (see docs/MODEL_EXPERIMENT_SUMMARY.md).
"""
import numpy as np
import pandas as pd


WINDOWS = (5, 10)
VENUE_WINDOW = 10

MODEL_FEATURES = [
    'd_margin_5', 'd_margin_10',
    'd_win_pct_5', 'd_win_pct_10',
    'home_wpct_home', 'away_wpct_away',
]


def add_matchup_diffs(games: pd.DataFrame) -> pd.DataFrame:
    games = games.copy()
    for n in WINDOWS:
        games[f'd_margin_{n}'] = games[f'home_margin_{n}'] - games[f'away_margin_{n}']
        games[f'd_win_pct_{n}'] = games[f'home_win_pct_{n}'] - games[f'away_win_pct_{n}']
    return games


def season_for_date(game_date: pd.Timestamp) -> int:
    return game_date.year + (1 if game_date.month >= 9 else 0)


def _team_results(prior: pd.DataFrame, team: str) -> pd.DataFrame:
    played = prior[(prior['home_team_id'] == team) | (prior['away_team_id'] == team)].sort_values('game_date_est')
    is_home = played['home_team_id'] == team
    return pd.DataFrame({
        'margin': np.where(is_home, played['home_team_points'] - played['away_team_points'],
                           played['away_team_points'] - played['home_team_points']),
        'won': is_home == played['home_team_wins'].astype(bool),
    })


def _venue_win_pct(prior: pd.DataFrame, team: str, at_home: bool) -> float:
    side = 'home_team_id' if at_home else 'away_team_id'
    recent = prior[prior[side] == team].sort_values('game_date_est').tail(VENUE_WINDOW)
    if recent.empty:
        return 0.5
    wins = recent['home_team_wins'].astype(bool)
    return float((wins if at_home else ~wins).mean())


def team_form(prior: pd.DataFrame, team: str) -> dict:
    """As-of form for one team, matching dataloader's training-time definitions."""
    results = _team_results(prior, team)
    form = {}
    for n in WINDOWS:
        recent = results.tail(n)
        form[f'win_pct_{n}'] = float(recent['won'].mean()) if len(recent) else 0.5
        form[f'margin_{n}'] = float(recent['margin'].mean()) if len(recent) else 0.0
    return form


def matchup_features(prior: pd.DataFrame, home_team: str, away_team: str) -> dict:
    """Model inputs for one upcoming game. `prior` must hold only earlier same-season games."""
    home, away = team_form(prior, home_team), team_form(prior, away_team)
    row = {f'home_{k}': v for k, v in home.items()}
    row.update({f'away_{k}': v for k, v in away.items()})
    row['home_wpct_home'] = _venue_win_pct(prior, home_team, at_home=True)
    row['away_wpct_away'] = _venue_win_pct(prior, away_team, at_home=False)
    return row
