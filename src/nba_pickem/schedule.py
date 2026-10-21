"""Fetch a day's NBA schedule from ESPN's public scoreboard and normalize it to DB team ids."""
from datetime import date

import pandas as pd
import requests


SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
REQUEST_TIMEOUT_SECONDS = 20

ESPN_TO_DB_TEAM = {'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'}
NBA_TEAMS = {
    'ATL', 'BKN', 'BOS', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW', 'HOU', 'IND', 'LAC', 'LAL', 'MEM',
    'MIA', 'MIL', 'MIN', 'NOP', 'NYK', 'OKC', 'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS',
}


def fetch_scoreboard(game_date: date) -> dict:
    response = requests.get(SCOREBOARD_URL, params={"dates": game_date.strftime("%Y%m%d")}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def parse_scoreboard(scoreboard: dict, game_date: date) -> pd.DataFrame:
    """One row per NBA-vs-NBA game; skips exhibition events (e.g. All-Star teams)."""
    games = []
    for event in scoreboard['events']:
        sides = {c['homeAway']: ESPN_TO_DB_TEAM.get(c['team']['abbreviation'], c['team']['abbreviation'])
                 for c in event['competitions'][0]['competitors']}
        if not {sides.get('home'), sides.get('away')} <= NBA_TEAMS:
            continue
        games.append({
            "game_id": f"espn-{event['id']}",
            "home_team_id": sides['home'],
            "away_team_id": sides['away'],
            "game_date_est": game_date,
        })
    return pd.DataFrame(games, columns=["game_id", "home_team_id", "away_team_id", "game_date_est"])
