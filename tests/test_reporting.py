from datetime import date

import duckdb

from nba_pickem.reporting import build_daily_report


def connection():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE teams (
            team_id VARCHAR PRIMARY KEY,
            league_id INTEGER,
            abbreviation VARCHAR,
            city VARCHAR,
            nickname VARCHAR
        );
        CREATE TABLE games (
            game_id VARCHAR PRIMARY KEY,
            home_team_id VARCHAR,
            away_team_id VARCHAR,
            game_date_est DATE,
            season INTEGER,
            home_team_points INTEGER,
            away_team_points INTEGER,
            home_team_wins BOOLEAN
        );
        CREATE TABLE game_predictions (
            game_id VARCHAR PRIMARY KEY,
            home_team_id VARCHAR,
            away_team_id VARCHAR,
            game_date_est DATE,
            predicted_home_team_wins BOOLEAN,
            home_win_probability DECIMAL(5,4)
        );
    """)
    conn.executemany(
        "INSERT INTO teams VALUES (?, 0, ?, ?, ?)",
        [
            ("MIL", "MIL", "Milwaukee", "Bucks"),
            ("CHI", "CHI", "Chicago", "Bulls"),
            ("BOS", "BOS", "Boston", "Celtics"),
            ("NYK", "NYK", "New York", "Knicks"),
        ],
    )
    return conn


def add_game(conn, game_id, game_date, home, away, home_won, predicted_home, probability):
    scores = (110, 100) if home_won is True else (99, 105) if home_won is False else (None, None)
    conn.execute(
        "INSERT INTO games VALUES (?, ?, ?, ?, 2027, ?, ?, ?)",
        [game_id, home, away, game_date, *scores, home_won],
    )
    conn.execute(
        "INSERT INTO game_predictions VALUES (?, ?, ?, ?, ?, ?)",
        [game_id, home, away, game_date, predicted_home, probability],
    )


def test_daily_report_separates_picks_and_performance_windows():
    conn = connection()
    add_game(conn, "mon", "2026-10-19", "MIL", "CHI", True, True, 0.7)
    add_game(conn, "tue-1", "2026-10-20", "BOS", "NYK", False, False, 0.4)
    add_game(conn, "tue-2", "2026-10-20", "MIL", "CHI", False, True, 0.6)
    add_game(conn, "wed", "2026-10-21", "BOS", "NYK", None, False, 0.35)

    report = build_daily_report(date(2026, 10, 21), conn)

    assert report["today"]["picks"] == [{
        "game_id": "wed",
        "away_team_id": "NYK",
        "away_team": "New York Knicks",
        "home_team_id": "BOS",
        "home_team": "Boston Celtics",
        "pick": "New York Knicks",
        "confidence": 0.65,
    }]
    assert {pick["game_id"]: pick["status"] for pick in report["previous_day"]["picks"]} == {
        "tue-1": "correct",
        "tue-2": "incorrect",
    }
    assert report["weekly"] == {
        "start_date": "2026-10-19",
        "end_date": "2026-10-20",
        "correct": 2,
        "graded": 3,
        "percentage": 66.7,
    }
    assert report["season_performance"]["correct"] == 2
    assert report["season_performance"]["graded"] == 3
    assert report["season_performance"]["percentage"] == 66.7


def test_empty_report_uses_null_percentage():
    report = build_daily_report(date(2026, 10, 21), connection())

    assert report["today"]["picks"] == []
    assert report["previous_day"]["picks"] == []
    assert report["weekly"]["percentage"] is None
    assert report["season_performance"]["percentage"] is None
