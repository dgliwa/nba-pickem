import json
from datetime import date
from pathlib import Path

from nba_pickem.dataloader import get_games
from nba_pickem.schedule import NBA_TEAMS, parse_scoreboard

FIXTURE = Path(__file__).parent / "fixtures" / "espn_scoreboard_20260410.json"


def test_parses_real_espn_response_into_db_team_ids():
    schedule = parse_scoreboard(json.loads(FIXTURE.read_text()), date(2026, 4, 10))

    assert len(schedule) == 15
    assert set(schedule['home_team_id']) | set(schedule['away_team_id']) <= NBA_TEAMS
    stored = get_games().query("game_date_est == '2026-04-10'")
    assert set(zip(schedule['home_team_id'], schedule['away_team_id'])) == set(zip(stored['home_team_id'], stored['away_team_id']))


def test_skips_exhibition_events():
    scoreboard = {'events': [{'id': '1', 'competitions': [{'competitors': [
        {'homeAway': 'home', 'team': {'abbreviation': 'STARS'}},
        {'homeAway': 'away', 'team': {'abbreviation': 'STRIPES'}}]}]}]}
    assert parse_scoreboard(scoreboard, date(2026, 2, 15)).empty
