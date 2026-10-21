import duckdb

from nba_pickem.season_sync import sync_games


def test_partial_sync_does_not_prune_unfetched_future_games():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE games (
            game_id VARCHAR PRIMARY KEY,
            home_team_id VARCHAR,
            away_team_id VARCHAR,
            game_date_est DATE,
            season INTEGER,
            home_team_points INTEGER,
            away_team_points INTEGER,
            home_team_wins BOOLEAN
        )
    """)
    october = {"date": "2026-10-21", "home_team": "MIL", "away_team": "WAS", "home_pts": None, "away_pts": None}
    november = {"date": "2026-11-21", "home_team": "BOS", "away_team": "NYK", "home_pts": None, "away_pts": None}
    sync_games(conn, 2027, [october, november])

    sync_games(conn, 2027, [october], prune_missing=False)

    assert conn.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 2
