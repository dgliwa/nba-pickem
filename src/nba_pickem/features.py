"""Model feature definitions shared by training and prediction.

Selected via walk-forward evaluation (see docs/MODEL_EXPERIMENT_SUMMARY.md).
"""
from datetime import date

import numpy as np
import pandas as pd


WINDOWS = (5, 10)
VENUE_WINDOW = 10

# FiveThirtyEight's NBA Elo parameters
ELO_START = 1500
ELO_K = 20
ELO_HOME_ADVANTAGE = 100
ELO_SEASON_CARRYOVER = 0.75  # keep 75% of a team's distance from the mean between seasons
BUBBLE = (date(2020, 7, 30), date(2020, 8, 14))  # neutral-site restart games: no home advantage

MODEL_FEATURES = ['d_elo']

# Previous model's inputs; rolling stats add nothing on top of Elo (see docs/MODEL_EXPERIMENT_SUMMARY.md)
ROLLING_FEATURES = [
    'd_margin_5', 'd_margin_10',
    'd_win_pct_5', 'd_win_pct_10',
    'home_wpct_home', 'away_wpct_away',
]


def add_matchup_diffs(games: pd.DataFrame) -> pd.DataFrame:
    games = games.copy()
    for n in WINDOWS:
        games[f'd_margin_{n}'] = games[f'home_margin_{n}'] - games[f'away_margin_{n}']
        games[f'd_win_pct_{n}'] = games[f'home_win_pct_{n}'] - games[f'away_win_pct_{n}']
    if 'home_elo_pre' in games:
        games['d_elo'] = games['home_elo_pre'].astype(float) - games['away_elo_pre'].astype(float)
    return games


def home_advantage(game_date) -> float:
    return 0.0 if BUBBLE[0] <= pd.Timestamp(game_date).date() <= BUBBLE[1] else ELO_HOME_ADVANTAGE


def elo_home_win_probability(home_elo: float, away_elo: float, hfa: float = ELO_HOME_ADVANTAGE) -> float:
    return 1 / (1 + 10 ** (-(home_elo + hfa - away_elo) / 400))


def compute_elo(games: pd.DataFrame) -> pd.DataFrame:
    """Pre-game Elo for every game, walking all seasons in date order.

    Ratings carry across seasons (regressed toward the mean), so a team's first game of a
    season still has an informative rating. Unplayed games get the teams' current ratings
    and don't update them. Returns game_id, home_elo_pre, away_elo_pre.
    """
    ratings: dict[str, float] = {}
    last_season: dict[str, int] = {}
    rows = []
    for g in games.sort_values(['game_date_est', 'game_id']).itertuples():
        for team in (g.home_team_id, g.away_team_id):
            if team in last_season and last_season[team] != g.season:
                ratings[team] = ELO_START + ELO_SEASON_CARRYOVER * (ratings[team] - ELO_START)
            last_season[team] = g.season
        home, away = ratings.get(g.home_team_id, ELO_START), ratings.get(g.away_team_id, ELO_START)
        rows.append((g.game_id, home, away))
        if pd.isna(g.home_team_wins):
            continue

        hfa = home_advantage(g.game_date_est)
        home_won = bool(g.home_team_wins)
        margin = abs(g.home_team_points - g.away_team_points)
        winner_edge = (home + hfa - away) * (1 if home_won else -1)
        mov_multiplier = (margin + 3) ** 0.8 / (7.5 + 0.006 * winner_edge)
        delta = ELO_K * mov_multiplier * (home_won - elo_home_win_probability(home, away, hfa))
        ratings[g.home_team_id] = home + delta
        ratings[g.away_team_id] = away - delta
    return pd.DataFrame(rows, columns=['game_id', 'home_elo_pre', 'away_elo_pre'])


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
