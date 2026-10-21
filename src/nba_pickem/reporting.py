"""Deterministic pick and performance reports for automation clients."""

from datetime import date, timedelta
from decimal import Decimal

import duckdb

from nba_pickem.dataloader import get_connection
from nba_pickem.features import season_for_date


def build_daily_report(report_date: date, connection: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Build today's picks plus prior-day, weekly, and season performance."""
    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        previous_date = report_date - timedelta(days=1)
        week_start = report_date - timedelta(days=report_date.weekday())
        season = season_for_date(report_date)
        return {
            "report_date": report_date.isoformat(),
            "season": int(season),
            "today": {
                "date": report_date.isoformat(),
                "picks": _picks_for_date(conn, report_date, include_results=False),
            },
            "previous_day": {
                "date": previous_date.isoformat(),
                "picks": _picks_for_date(conn, previous_date, include_results=True),
            },
            "weekly": _performance(conn, week_start, previous_date),
            "season_performance": _season_performance(conn, int(season), previous_date),
        }
    finally:
        if owns_connection:
            conn.close()


def _picks_for_date(conn: duckdb.DuckDBPyConnection, game_date: date, *, include_results: bool) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            gp.game_id,
            gp.home_team_id,
            gp.away_team_id,
            COALESCE(th.city || ' ' || th.nickname, gp.home_team_id) AS home_team,
            COALESCE(ta.city || ' ' || ta.nickname, gp.away_team_id) AS away_team,
            gp.predicted_home_team_wins,
            gp.home_win_probability,
            g.home_team_points,
            g.away_team_points,
            g.home_team_wins
        FROM game_predictions gp
        LEFT JOIN games g ON g.game_id = gp.game_id
        LEFT JOIN teams th ON th.team_id = gp.home_team_id
        LEFT JOIN teams ta ON ta.team_id = gp.away_team_id
        WHERE gp.game_date_est = ?
        ORDER BY gp.away_team_id, gp.home_team_id
        """,
        [game_date],
    ).fetchall()

    picks = []
    for row in rows:
        (
            game_id,
            home_id,
            away_id,
            home_team,
            away_team,
            predicted_home,
            home_probability,
            home_points,
            away_points,
            home_won,
        ) = row
        probability = _as_float(home_probability)
        predicted_team = home_team if predicted_home else away_team
        pick = {
            "game_id": game_id,
            "away_team_id": away_id,
            "away_team": away_team,
            "home_team_id": home_id,
            "home_team": home_team,
            "pick": predicted_team,
            "confidence": round(probability if predicted_home else 1 - probability, 4),
        }
        if include_results:
            graded = home_won is not None
            pick.update({
                "status": "correct" if graded and bool(predicted_home) == bool(home_won) else "incorrect" if graded else "pending",
                "actual_winner": home_team if home_won is True else away_team if home_won is False else None,
                "score": f"{away_points}-{home_points}" if graded else None,
            })
        picks.append(pick)
    return picks


def _performance(conn: duckdb.DuckDBPyConnection, start_date: date, end_date: date) -> dict:
    if end_date < start_date:
        return _performance_result(start_date, end_date, 0, 0)
    correct, graded = conn.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE gp.predicted_home_team_wins = g.home_team_wins),
            COUNT(*)
        FROM game_predictions gp
        JOIN games g ON g.game_id = gp.game_id
        WHERE gp.game_date_est BETWEEN ? AND ?
          AND g.home_team_wins IS NOT NULL
        """,
        [start_date, end_date],
    ).fetchone()
    return _performance_result(start_date, end_date, int(correct), int(graded))


def _season_performance(conn: duckdb.DuckDBPyConnection, season: int, end_date: date) -> dict:
    correct, graded = conn.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE gp.predicted_home_team_wins = g.home_team_wins),
            COUNT(*)
        FROM game_predictions gp
        JOIN games g ON g.game_id = gp.game_id
        WHERE g.season = ?
          AND gp.game_date_est <= ?
          AND g.home_team_wins IS NOT NULL
        """,
        [season, end_date],
    ).fetchone()
    result = _performance_result(None, end_date, int(correct), int(graded))
    result["season"] = season
    return result


def _performance_result(start_date: date | None, end_date: date, correct: int, graded: int) -> dict:
    return {
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat(),
        "correct": correct,
        "graded": graded,
        "percentage": round(100 * correct / graded, 1) if graded else None,
    }


def _as_float(value: Decimal | float) -> float:
    return float(value)
