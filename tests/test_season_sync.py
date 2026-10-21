import duckdb
import pytest

from nba_pickem.scripts import load_bball_ref_data as loader
from nba_pickem.season_sync import sync_games

SCHEDULE_HTML = """
<table id="schedule"><tbody>
<tr><th data-stat="date_game"><a>Tue, Oct 20, 2026</a></th>
  <td data-stat="visitor_team_name"><a href="/teams/BOS/2027.html">Boston Celtics</a></td><td data-stat="visitor_pts">115</td>
  <td data-stat="home_team_name"><a href="/teams/DET/2027.html">Detroit Pistons</a></td><td data-stat="home_pts">120</td></tr>
<tr><th data-stat="date_game"><a>Wed, Oct 21, 2026</a></th>
  <td data-stat="visitor_team_name"><a href="/teams/WAS/2027.html">Washington Wizards</a></td><td data-stat="visitor_pts"></td>
  <td data-stat="home_team_name"><a href="/teams/MIL/2027.html">Milwaukee Bucks</a></td><td data-stat="home_pts"></td></tr>
</tbody></table>
"""


def game(date, home, away, home_pts=None, away_pts=None):
    return {"date": date, "home_team": home, "away_team": away, "home_pts": home_pts, "away_pts": away_pts}


@pytest.fixture
def conn():
    connection = duckdb.connect(":memory:")
    connection.execute("""
        CREATE TABLE games (game_id VARCHAR PRIMARY KEY, home_team_id VARCHAR, away_team_id VARCHAR,
            game_date_est DATE, season INTEGER, home_team_points INTEGER, away_team_points INTEGER, home_team_wins BOOLEAN)
    """)
    return connection


def outcomes(conn):
    return conn.execute("SELECT game_id, home_team_wins FROM games ORDER BY game_id").fetchall()


def test_parser_keeps_unplayed_games_without_scores(monkeypatch):
    monkeypatch.setattr(loader, "normalize_team", lambda abbrev: abbrev)

    played, unplayed = loader.parse_season(SCHEDULE_HTML, 2027)

    assert (played["home_team"], played["home_pts"], played["away_pts"]) == ("DET", 120, 115)
    assert (unplayed["home_team"], unplayed["away_team"], unplayed["home_pts"]) == ("MIL", "WAS", None)


def test_unplayed_game_is_stored_then_gains_result(conn):
    assert sync_games(conn, 2027, [game("2026-10-21", "MIL", "WAS")]) == 0
    assert outcomes(conn) == [("MILWAS20272026" "1021", None)]

    assert sync_games(conn, 2027, [game("2026-10-21", "MIL", "WAS", 99, 101)]) == 1
    assert outcomes(conn) == [("MILWAS20272026" "1021", False)]


def test_already_played_game_is_not_counted_again(conn):
    played = [game("2026-10-20", "DET", "BOS", 120, 115)]
    assert sync_games(conn, 2027, played) == 1
    assert sync_games(conn, 2027, played) == 0


def test_postponed_game_is_dropped_and_rescheduled_one_added(conn):
    sync_games(conn, 2027, [game("2026-10-21", "MIL", "WAS")])
    sync_games(conn, 2027, [game("2026-10-23", "MIL", "WAS")])

    assert [g for g, _ in outcomes(conn)] == ["MILWAS202720261023"]


def test_failed_scrape_does_not_wipe_stored_schedule(conn):
    sync_games(conn, 2027, [game("2026-10-21", "MIL", "WAS")])
    sync_games(conn, 2027, [])

    assert len(outcomes(conn)) == 1


def test_playoff_games_are_skipped(conn):
    from datetime import date
    sync_games(conn, 2027, [game("2027-04-20", "MIL", "WAS")], playoffs_start=date(2027, 4, 19))

    assert outcomes(conn) == []
