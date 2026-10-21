"""Reconcile scraped schedule rows (played and unplayed) with the games table."""
from datetime import date


def scraped_game_id(game: dict, season: int) -> str:
    return f"{game['home_team']}{game['away_team']}{season}{game['date'].replace('-', '')}"


def has_result(game: dict) -> bool:
    home, away = game["home_pts"], game["away_pts"]
    return home is not None and away is not None and (home, away) != (0, 0)


def sync_games(
    conn,
    season: int,
    scraped: list[dict],
    playoffs_start: date | None = None,
    *,
    prune_missing: bool = True,
) -> int:
    """Insert games and results, optionally dropping unplayed games absent from a full-season fetch.

    Returns the number of games that gained a result.
    """
    has_result_in_db = dict(conn.execute(
        "SELECT game_id, home_team_wins IS NOT NULL FROM games WHERE season = ?", [season]
    ).fetchall())
    scheduled_ids = set()
    newly_scored = 0

    for game in scraped:
        if playoffs_start and date.fromisoformat(game["date"]) >= playoffs_start:
            continue
        game_id = scraped_game_id(game, season)
        scheduled_ids.add(game_id)
        scored = has_result(game)
        home_wins = game["home_pts"] > game["away_pts"] if scored else None
        points = [game["home_pts"], game["away_pts"]] if scored else [None, None]

        if game_id not in has_result_in_db:
            conn.execute("""
                INSERT INTO games (game_id, home_team_id, away_team_id, game_date_est, season,
                                   home_team_points, away_team_points, home_team_wins)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [game_id, game["home_team"], game["away_team"], game["date"], season, *points, home_wins])
        elif scored and not has_result_in_db[game_id]:
            conn.execute(
                "UPDATE games SET home_team_points = ?, away_team_points = ?, home_team_wins = ? WHERE game_id = ?",
                [*points, home_wins, game_id],
            )
        else:
            continue
        newly_scored += scored

    if prune_missing and scheduled_ids:
        stale = [
            game_id for game_id, played in has_result_in_db.items()
            if not played and game_id not in scheduled_ids
        ]
        for game_id in stale:
            conn.execute("DELETE FROM games WHERE game_id = ?", [game_id])

    return newly_scored
