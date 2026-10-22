#!/usr/bin/env python3
"""NBA Pick'em - Load moneyline odds from sportsbookreview.com

One request per date returns every game's opening line and latest line for each sportsbook.
Fetched after a game, the latest line is the closing line. SBR has NBA odds from the
2019-20 season (season 2020) on.

Usage:
    nba-pickem-load-odds --since 2020     # Backfill every stored game date from 2019-20 on
    nba-pickem-load-odds --date 2025-01-15
"""
import argparse
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from nba_pickem.dataloader import get_connection, get_teams, save_moneylines
from nba_pickem.features import season_for_date
from nba_pickem.scripts.load_bball_ref_data import HEADERS

FIRST_ODDS_SEASON = 2020
ODDS_URL = "https://www.sportsbookreview.com/betting-odds/nba-basketball/money-line/full-game/?date={}"
# SBR's latest line for these game dates is an in-game price, not the close: big moves from the
# opener go toward the eventual winner 88-100% of the time (vs ~65% in other months)
IN_GAME_LATEST = [(date(2019, 10, 1), date(2019, 11, 30)), (date(2020, 7, 1), date(2020, 7, 31)),
                  (date(2021, 10, 1), date(2021, 11, 30))]
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
EASTERN = ZoneInfo("US/Eastern")


def valid_line(line: dict) -> bool:
    """Both sides present and plausible; SBR uses -10000 and 2**31-1 as placeholders."""
    return all(isinstance(line.get(k), int) and 100 <= abs(line[k]) < 10000 for k in ("homeOdds", "awayOdds"))


def closing_line_unreliable(game_date: date) -> bool:
    return any(start <= game_date <= end for start, end in IN_GAME_LATEST)


def parse_odds_page(html: str, team_ids: dict[str, str]) -> list[dict]:
    """One row per game and sportsbook. team_ids maps SBR team nicknames to our team ids."""
    data = json.loads(NEXT_DATA.search(html).group(1))
    tables = data["props"]["pageProps"].get("oddsTables") or []
    rows = []
    for table in tables:
        for game in table["oddsTableModel"]["gameRows"]:
            view = game["gameView"]
            home, away = team_ids.get(view["homeTeam"]["nickname"]), team_ids.get(view["awayTeam"]["nickname"])
            if not home or not away:
                continue  # All-Star and other non-NBA-team games
            game_date = datetime.fromisoformat(view["startDate"]).astimezone(EASTERN).date()
            season = season_for_date(pd.Timestamp(game_date))
            for odds in game["oddsViews"]:
                opening, latest = (odds or {}).get("openingLine") or {}, (odds or {}).get("currentLine") or {}
                if not valid_line(opening):
                    opening = {}
                if not valid_line(latest) or closing_line_unreliable(game_date):
                    latest = {}
                if not opening and not latest:
                    continue
                rows.append({
                    "game_id": f"{home}{away}{season}{game_date.strftime('%Y%m%d')}",
                    "sportsbook": odds["sportsbook"],
                    "game_date_est": game_date,
                    "open_home_odds": opening.get("homeOdds"),
                    "open_away_odds": opening.get("awayOdds"),
                    "latest_home_odds": latest.get("homeOdds"),
                    "latest_away_odds": latest.get("awayOdds"),
                })
    return rows


def team_ids_by_nickname() -> dict[str, str]:
    teams = get_teams()
    return dict(zip(teams["nickname"], teams["team_id"]))


def fetch_odds_page(odds_date: date, attempts: int = 4) -> str:
    """GET one date's page, backing off on server errors and timeouts."""
    for attempt in range(attempts):
        try:
            response = requests.get(ODDS_URL.format(odds_date.isoformat()), headers=HEADERS, timeout=30)
            if response.status_code < 500:
                response.raise_for_status()
                return response.text
        except (requests.ConnectionError, requests.Timeout):
            if attempt == attempts - 1:
                raise
        time.sleep(10 * 2 ** attempt)
    response.raise_for_status()


def load_odds_for_date(odds_date: date, team_ids: dict[str, str] | None = None) -> int:
    """Fetch and store one date's odds. Returns rows stored for games in the games table."""
    rows = pd.DataFrame(parse_odds_page(fetch_odds_page(odds_date), team_ids or team_ids_by_nickname()))
    if rows.empty:
        print(f"  {odds_date}: no odds")
        return 0

    conn = get_connection()
    known = {r[0] for r in conn.execute(
        "SELECT game_id FROM games WHERE game_date_est = ?", [odds_date]
    ).fetchall()}
    conn.close()
    unmatched = sorted(set(rows["game_id"]) - known)
    rows = rows[rows["game_id"].isin(known)].assign(fetched_at=datetime.now(timezone.utc).replace(tzinfo=None))
    save_moneylines(rows)
    print(f"  {odds_date}: {rows['game_id'].nunique()} games, {len(rows)} lines"
          + (f"; unmatched {unmatched}" if unmatched else ""))
    return len(rows)


def dates_missing_closing_lines(first_season: int) -> list[date]:
    """Stored game dates up to today whose games have no odds fetched after the date passed."""
    conn = get_connection()
    dates = conn.execute("""
        SELECT DISTINCT g.game_date_est
        FROM games g
        LEFT JOIN moneylines m ON m.game_id = g.game_id AND m.fetched_at::DATE > g.game_date_est
        WHERE g.season >= ? AND g.game_date_est < current_date AND m.game_id IS NULL
        ORDER BY 1
    """, [first_season]).fetchall()
    conn.close()
    return [d[0] for d in dates]


def refresh_recent_odds(today: date):
    """Daily: yesterday's closing lines and today's current lines. Never fails the caller."""
    team_ids = team_ids_by_nickname()
    for odds_date in (today - timedelta(days=1), today):
        try:
            load_odds_for_date(odds_date, team_ids)
        except Exception as error:  # odds are optional for picks
            print(f"  {odds_date}: odds refresh failed ({error})")


def backfill(first_season: int):
    team_ids = team_ids_by_nickname()
    dates = dates_missing_closing_lines(first_season)
    print(f"Fetching odds for {len(dates)} dates from season {first_season}...")
    failed = []
    for odds_date in dates:
        try:
            load_odds_for_date(odds_date, team_ids)
        except requests.RequestException as error:
            print(f"  {odds_date}: failed ({error}); rerun to retry")
            failed.append(odds_date)
        time.sleep(3)  # Be polite to SBR
    if failed:
        print(f"{len(failed)} dates failed: {[d.isoformat() for d in failed]}")


def main():
    parser = argparse.ArgumentParser(description="Load NBA moneyline odds from sportsbookreview.com")
    parser.add_argument("--since", type=int, help=f"Backfill closing lines from this season (earliest {FIRST_ODDS_SEASON})")
    parser.add_argument("--date", help="Fetch one date's odds (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.date:
        load_odds_for_date(date.fromisoformat(args.date))
    elif args.since:
        backfill(max(args.since, FIRST_ODDS_SEASON))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
