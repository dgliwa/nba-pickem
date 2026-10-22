import json

from nba_pickem.scripts.load_odds import parse_odds_page

TEAMS = {"76ers": "PHI", "Knicks": "NYK"}


def page(start, odds_views):
    game = {"gameView": {"startDate": start, "homeTeam": {"nickname": "76ers"}, "awayTeam": {"nickname": "Knicks"}},
            "oddsViews": odds_views}
    data = {"props": {"pageProps": {"oddsTables": [{"oddsTableModel": {"gameRows": [game]}}]}}}
    return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>'


def line(home, away):
    return {"homeOdds": home, "awayOdds": away}


def test_parses_open_and_latest_lines_on_the_eastern_date():
    rows = parse_odds_page(page("2025-01-16T00:00:00+00:00", [
        {"sportsbook": "fanduel", "openingLine": line(210, -255), "currentLine": line(176, -210)}, None,
    ]), TEAMS)
    assert rows == [{"game_id": "PHINYK202520250115", "sportsbook": "fanduel", "game_date_est": rows[0]["game_date_est"],
                     "open_home_odds": 210, "open_away_odds": -255, "latest_home_odds": 176, "latest_away_odds": -210}]
    assert rows[0]["game_date_est"].isoformat() == "2025-01-15"


def test_placeholder_odds_are_dropped():
    rows = parse_odds_page(page("2025-01-16T00:00:00+00:00", [
        {"sportsbook": "betmgm", "openingLine": line(-10000, -10000), "currentLine": line(170, -210)},
        {"sportsbook": "bet365", "openingLine": line(2147483647, 2147483647), "currentLine": line(2147483647, 2147483647)},
    ]), TEAMS)
    assert [(r["sportsbook"], r["open_home_odds"], r["latest_home_odds"]) for r in rows] == [("betmgm", None, 170)]


def test_in_game_latest_lines_are_not_kept_as_closes():
    rows = parse_odds_page(page("2021-10-20T23:30:00+00:00", [
        {"sportsbook": "fanduel", "openingLine": line(150, -170), "currentLine": line(-2000, 1100)},
    ]), TEAMS)
    assert (rows[0]["open_home_odds"], rows[0]["latest_home_odds"]) == (150, None)
