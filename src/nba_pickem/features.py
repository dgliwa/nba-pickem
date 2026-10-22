"""Model feature definitions shared by training and prediction.

Selected via walk-forward evaluation (see docs/MODEL_EXPERIMENT_SUMMARY.md).
"""
from datetime import date

import numpy as np
import pandas as pd


WINDOWS = (5, 10)
VENUE_WINDOW = 10

# FiveThirtyEight's NBA Elo parameters, with home advantage and rest re-tuned on 2016-2023
ELO_START = 1500
ELO_K = 20
ELO_HOME_ADVANTAGE = 55  # FiveThirtyEight used 100; home teams win less often than they used to
ELO_SEASON_CARRYOVER = 0.75  # keep 75% of a team's distance from the mean between seasons
BUBBLE = (date(2020, 7, 30), date(2020, 8, 14))  # neutral-site restart games: no home advantage
# Schedule-context adjustments in Elo points, tuned on 2016-2023 (see docs/MODEL_EXPERIMENT_SUMMARY.md)
ELO_B2B_PENALTY = 45
ELO_TRAVEL_PENALTY = 0  # per cube root of miles travelled since the previous game; no signal found

BUBBLE_SITE = (28.34, -81.55)  # Walt Disney World, Orlando
ARENAS = {  # (latitude, longitude) of each team's home arena city
    'ATL': (33.76, -84.40), 'BKN': (40.68, -73.98), 'BOS': (42.37, -71.06), 'CHA': (35.23, -80.84),
    'CHI': (41.88, -87.67), 'CLE': (41.50, -81.69), 'DAL': (32.79, -96.81), 'DEN': (39.75, -105.01),
    'DET': (42.34, -83.06), 'GSW': (37.77, -122.39), 'HOU': (29.75, -95.36), 'IND': (39.76, -86.16),
    'LAC': (34.04, -118.27), 'LAL': (34.04, -118.27), 'MEM': (35.14, -90.05), 'MIA': (25.78, -80.19),
    'MIL': (43.05, -87.92), 'MIN': (44.98, -93.28), 'NOP': (29.95, -90.08), 'NYK': (40.75, -73.99),
    'OKC': (35.46, -97.52), 'ORL': (28.54, -81.38), 'PHI': (39.90, -75.17), 'PHX': (33.45, -112.07),
    'POR': (45.53, -122.67), 'SAC': (38.58, -121.50), 'SAS': (29.43, -98.44), 'TOR': (43.64, -79.38),
    'UTA': (40.77, -111.90), 'WAS': (38.90, -77.02),
}

MODEL_FEATURES = ['d_elo_adj']  # Elo difference plus the back-to-back adjustment

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
    if 'elo_context_adj' in games:
        games['d_elo_adj'] = games['d_elo'] + games['elo_context_adj'].astype(float)
    return games


def in_bubble(game_date) -> bool:
    return BUBBLE[0] <= pd.Timestamp(game_date).date() <= BUBBLE[1]


def home_advantage(game_date, base: float = ELO_HOME_ADVANTAGE) -> float:
    return 0.0 if in_bubble(game_date) else base


def _miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(np.radians, (*a, *b))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return float(3958.8 * 2 * np.arcsin(np.sqrt(h)))


def schedule_context(games: pd.DataFrame) -> pd.DataFrame:
    """Back-to-back flags and miles travelled since each team's previous game.

    Uses the schedule, not results, so upcoming games get context too. A team's first game
    of a season has no back-to-back and no travel.
    Returns game_id, home_team_b2b, away_team_b2b, home_travel_miles, away_travel_miles.
    """
    last: dict[str, tuple[int, pd.Timestamp, tuple[float, float]]] = {}
    rows = []
    for g in games.sort_values(['game_date_est', 'game_id']).itertuples():
        site = BUBBLE_SITE if in_bubble(g.game_date_est) else ARENAS[g.home_team_id]
        row = [g.game_id]
        for team in (g.home_team_id, g.away_team_id):
            prev = last.get(team)
            same_season = prev is not None and prev[0] == g.season
            row.append(same_season and (g.game_date_est - prev[1]).days == 1)
            row.append(_miles(prev[2], site) if same_season else 0.0)
            last[team] = (g.season, g.game_date_est, site)
        rows.append(row)
    context = pd.DataFrame(rows, columns=['game_id', 'home_team_b2b', 'home_travel_miles',
                                          'away_team_b2b', 'away_travel_miles'])
    return context[['game_id', 'home_team_b2b', 'away_team_b2b', 'home_travel_miles', 'away_travel_miles']]


def context_adjustment(home_b2b, away_b2b, home_miles, away_miles,
                       b2b_penalty: float = ELO_B2B_PENALTY, travel_penalty: float = ELO_TRAVEL_PENALTY) -> float:
    """Elo points added to the home side for rest and travel (positive favours home)."""
    return (b2b_penalty * (int(away_b2b) - int(home_b2b))
            + travel_penalty * (np.cbrt(away_miles) - np.cbrt(home_miles)))


def elo_home_win_probability(home_elo: float, away_elo: float, hfa: float = ELO_HOME_ADVANTAGE) -> float:
    return 1 / (1 + 10 ** (-(home_elo + hfa - away_elo) / 400))


def compute_elo(games: pd.DataFrame, b2b_penalty: float = ELO_B2B_PENALTY,
                travel_penalty: float = ELO_TRAVEL_PENALTY, home_adv: float = ELO_HOME_ADVANTAGE) -> pd.DataFrame:
    """Pre-game Elo for every game, walking all seasons in date order.

    Ratings carry across seasons (regressed toward the mean), so a team's first game of a
    season still has an informative rating. Unplayed games get the teams' current ratings
    and don't update them. Rest and travel shift the expected result (and so the update)
    but not the ratings themselves.
    Returns game_id, home_elo_pre, away_elo_pre, elo_context_adj, plus schedule_context columns.
    """
    context = schedule_context(games)
    games = games.merge(context, on='game_id')
    ratings: dict[str, float] = {}
    last_season: dict[str, int] = {}
    rows = []
    for g in games.sort_values(['game_date_est', 'game_id']).itertuples():
        for team in (g.home_team_id, g.away_team_id):
            if team in last_season and last_season[team] != g.season:
                ratings[team] = ELO_START + ELO_SEASON_CARRYOVER * (ratings[team] - ELO_START)
            last_season[team] = g.season
        home, away = ratings.get(g.home_team_id, ELO_START), ratings.get(g.away_team_id, ELO_START)
        adj = context_adjustment(g.home_team_b2b, g.away_team_b2b, g.home_travel_miles, g.away_travel_miles,
                                 b2b_penalty, travel_penalty)
        rows.append((g.game_id, home, away, adj))
        if pd.isna(g.home_team_wins):
            continue

        hfa = home_advantage(g.game_date_est, home_adv) + adj
        home_won = bool(g.home_team_wins)
        margin = abs(g.home_team_points - g.away_team_points)
        winner_edge = (home + hfa - away) * (1 if home_won else -1)
        mov_multiplier = (margin + 3) ** 0.8 / (7.5 + 0.006 * winner_edge)
        delta = ELO_K * mov_multiplier * (home_won - elo_home_win_probability(home, away, hfa))
        ratings[g.home_team_id] = home + delta
        ratings[g.away_team_id] = away - delta
    elo = pd.DataFrame(rows, columns=['game_id', 'home_elo_pre', 'away_elo_pre', 'elo_context_adj'])
    return elo.merge(context, on='game_id')


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
