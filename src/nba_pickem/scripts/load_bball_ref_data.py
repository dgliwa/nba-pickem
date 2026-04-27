#!/usr/bin/env python3
"""NBA Pick'em - Load Data from Basketball-Reference

Uses requests to fetch league schedule pages directly.

Usage:
    nba-pickem-load-bball-ref --teams
    nba-pickem-load-bball-ref --season 2025
    nba-pickem-load-bball-ref --all-seasons --compute-features
"""
import argparse
import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup

from nba_pickem.config import DB_PATH
from nba_pickem.dataloader import get_connection

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.basketball-reference.com/",
}


def update_playoffs_start_date(season: int) -> bool:
    """Fetch playoffs start date from Basketball-Reference and update seasons table.
    
    Returns:
        True if playoffs date found and updated, False otherwise
    """
    playoffs_url = f"https://www.basketball-reference.com/playoffs/NBA_{season}_games.html"
    
    try:
        resp = requests.get(playoffs_url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            print(f"  Playoffs page not found for season {season}")
            return False
        
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "schedule"})
        if not table:
            return False
        
        tbody = table.find("tbody")
        if not tbody:
            return False
        
        # Get first playoff game date
        for row in tbody.find_all("tr"):
            if row.get("class") and "thead" in row.get("class"):
                continue
            
            date_cell = row.find("th", {"data-stat": "date_game"})
            if not date_cell:
                continue
            
            date_link = date_cell.find("a")
            if not date_link:
                continue
            
            date_text = date_link.get_text(strip=True)
            if not date_text:
                continue
            
            # Parse the date - format is like "Sat, Apr 19, 2025" or "April 19, 2025"
            from datetime import datetime
            try:
                # Try with day of week first
                try:
                    playoff_date = datetime.strptime(date_text, "%a, %b %d, %Y").date()
                except ValueError:
                    playoff_date = datetime.strptime(date_text, "%B %d, %Y").date()
            except ValueError:
                continue
            
            # Update seasons table
            conn = get_connection()
            conn.execute("""
                UPDATE seasons SET playoffs_start_date = ? WHERE season_year = ?
            """, [playoff_date, season])
            conn.commit()
            conn.close()
            
            print(f"  Season {season} playoffs start: {playoff_date}")
            return True
        
        return False
        
    except Exception as e:
        print(f"  Error fetching playoffs date: {e}")
        return False


def ensure_tables():
    """Ensure team_aliases table exists."""
    conn = get_connection()
    
    # Check if team_aliases table exists
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='team_aliases'").fetchall()
    if not tables:
        conn.execute("""
            CREATE TABLE team_aliases (
                legacy_abbrev VARCHAR(4) PRIMARY KEY,
                canonical_abbrev VARCHAR(4) NOT NULL
            )
        """)
        conn.commit()
        print("Created team_aliases table")
    conn.close()


def load_team_aliases():
    """Load canonical team abbrevs and legacy aliases."""
    ensure_tables()
    
    conn = get_connection()
    conn.execute("DELETE FROM team_aliases")
    
    # Map legacy abbreviations to canonical
    aliases = [
        ("BRK", "BKN"),  # Brooklyn
        ("CHO", "CHA"),  # Charlotte
        ("PHO", "PHX"),  # Phoenix
    ]
    
    conn.executemany("INSERT INTO team_aliases (legacy_abbrev, canonical_abbrev) VALUES (?, ?)", aliases)
    conn.commit()
    print(f"Loaded {len(aliases)} team aliases")
    conn.close()


def load_teams():
    """Load teams with bball-ref abbreviations as IDs."""
    conn = get_connection()
    conn.execute("DELETE FROM teams")
    
    # All 30 NBA teams with canonical abbreviations (team_id = abbreviation)
    teams = [
        ("ATL", 0, "ATL", "Atlanta", "Hawks"),
        ("BKN", 0, "BKN", "Brooklyn", "Nets"),
        ("BOS", 0, "BOS", "Boston", "Celtics"),
        ("CHA", 0, "CHA", "Charlotte", "Hornets"),
        ("CHI", 0, "CHI", "Chicago", "Bulls"),
        ("CLE", 0, "CLE", "Cleveland", "Cavaliers"),
        ("DAL", 0, "DAL", "Dallas", "Mavericks"),
        ("DEN", 0, "DEN", "Denver", "Nuggets"),
        ("DET", 0, "DET", "Detroit", "Pistons"),
        ("GSW", 0, "GSW", "Golden State", "Warriors"),
        ("HOU", 0, "HOU", "Houston", "Rockets"),
        ("IND", 0, "IND", "Indiana", "Pacers"),
        ("LAC", 0, "LAC", "Los Angeles", "Clippers"),
        ("LAL", 0, "LAL", "Los Angeles", "Lakers"),
        ("MEM", 0, "MEM", "Memphis", "Grizzlies"),
        ("MIA", 0, "MIA", "Miami", "Heat"),
        ("MIL", 0, "MIL", "Milwaukee", "Bucks"),
        ("MIN", 0, "MIN", "Minnesota", "Timberwolves"),
        ("NOP", 0, "NOP", "New Orleans", "Pelicans"),
        ("NYK", 0, "NYK", "New York", "Knicks"),
        ("OKC", 0, "OKC", "Oklahoma City", "Thunder"),
        ("ORL", 0, "ORL", "Orlando", "Magic"),
        ("PHI", 0, "PHI", "Philadelphia", "76ers"),
        ("PHX", 0, "PHX", "Phoenix", "Suns"),
        ("POR", 0, "POR", "Portland", "Trail Blazers"),
        ("SAC", 0, "SAC", "Sacramento", "Kings"),
        ("SAS", 0, "SAS", "San Antonio", "Spurs"),
        ("TOR", 0, "TOR", "Toronto", "Raptors"),
        ("UTA", 0, "UTA", "Utah", "Jazz"),
        ("WAS", 0, "WAS", "Washington", "Wizards"),
    ]
    
    conn.executemany("INSERT INTO teams VALUES (?, ?, ?, ?, ?)", teams)
    conn.commit()
    print(f"Loaded {len(teams)} teams")
    conn.close()


def normalize_team(abbrev: str) -> str:
    """Convert legacy abbreviations to canonical form."""
    conn = get_connection()
    try:
        result = conn.execute(
            "SELECT canonical_abbrev FROM team_aliases WHERE legacy_abbrev = ?",
            [abbrev]
        ).fetchone()
        
        if result:
            return result[0]
        return abbrev
    finally:
        conn.close()


def fetch_season_page(season: int) -> str:
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games.html"
    print(f"Fetching {url}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_all_pages(season: int) -> list:
    base_url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games"
    urls = []
    
    soup = BeautifulSoup(requests.get(base_url + ".html", headers=HEADERS, timeout=30).text, "html.parser")
    
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if f"NBA_{season}_games-" in href and href.endswith(".html"):
            full_url = "https://www.basketball-reference.com" + href
            if full_url not in urls:
                urls.append(full_url)
    
    if not urls:
        urls = [base_url + ".html"]
    
    print(f"Found {len(urls)} pages for season {season}")
    time.sleep(6)
    return urls


def parse_season(html: str, season: int) -> list:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "schedule"})
    if not table:
        print("No schedule table found")
        return []
    
    tbody = table.find("tbody")
    if not tbody:
        return []
    
    games = []
    for row in tbody.find_all("tr"):
        if row.get("class") and "thead" in row.get("class"):
            continue
        
        date_cell = row.find("th", {"data-stat": "date_game"})
        if not date_cell:
            continue
        
        date_link = date_cell.find("a")
        if not date_link:
            continue
        
        date_text = date_link.get_text(strip=True)
        
        visitor_pts_cell = row.find("td", {"data-stat": "visitor_pts"})
        home_pts_cell = row.find("td", {"data-stat": "home_pts"})
        
        if not visitor_pts_cell or not home_pts_cell:
            continue
        
        visitor_pts_text = visitor_pts_cell.get_text(strip=True)
        home_pts_text = home_pts_cell.get_text(strip=True)
        
        if not visitor_pts_text or not home_pts_text:
            continue
        
        if visitor_pts_text == "-" or home_pts_text == "-":
            continue
        
        try:
            visitor_pts = int(visitor_pts_text)
            home_pts = int(home_pts_text)
        except ValueError:
            continue
        
        visitor_team_cell = row.find("td", {"data-stat": "visitor_team_name"})
        home_team_cell = row.find("td", {"data-stat": "home_team_name"})
        
        if not visitor_team_cell or not home_team_cell:
            continue
        
        visitor_link = visitor_team_cell.find("a")
        home_link = home_team_cell.find("a")
        
        if not visitor_link or not home_link:
            continue
        
        # Get raw abbreviations from URL
        visitor_href = visitor_link.get("href", "")
        home_href = home_link.get("href", "")
        
        raw_visitor_abbrev = visitor_href.split("/")[-2] if visitor_href else ""
        raw_home_abbrev = home_href.split("/")[-2] if home_href else ""
        
        # Normalize to canonical form
        visitor_abbrev = normalize_team(raw_visitor_abbrev)
        home_abbrev = normalize_team(raw_home_abbrev)
        
        from datetime import datetime
        try:
            game_date = datetime.strptime(date_text, "%a, %b %d, %Y")
        except ValueError:
            try:
                game_date = datetime.strptime(date_text, "%b %d, %Y")
            except:
                continue
        
        games.append({
            "date": game_date.strftime("%Y-%m-%d"),
            "home_team": home_abbrev,
            "away_team": visitor_abbrev,
            "home_pts": home_pts,
            "away_pts": visitor_pts,
            "season": season,
        })
    
    return games


def load_season(season: int, force: bool = False, incremental: bool = True) -> int:
    """Load games for a season.
    
    Args:
        season: The season year (e.g., 2025 for 2025-2026)
        force: If True, delete existing games first
        incremental: If True (default), only load NEW games not in DB
    
    Returns:
        Number of NEW games loaded
    """
    from datetime import date as Date
    
    print(f"Loading season {season}...")
    
    # First, fetch and update playoffs start date
    print(f"  Checking playoffs start date...")
    update_playoffs_start_date(season)
    
    # Get playoffs start date from DB
    conn = get_connection()
    playoffs_result = conn.execute("""
        SELECT playoffs_start_date FROM seasons WHERE season_year = ?
    """, [season]).fetchone()
    playoffs_start = playoffs_result[0] if playoffs_result else None
    
    if force:
        conn.execute(f"DELETE FROM games WHERE season = {season}")
        print(f"  Cleared existing {season} games")
    
    existing_ids = set()
    if incremental and not force:
        existing_ids = set(r[0] for r in conn.execute(
            "SELECT game_id FROM games WHERE season = ?", [season]
        ).fetchall())
        print(f"  Found {len(existing_ids)} existing games in DB")
    
    urls = fetch_all_pages(season)
    
    all_games = []
    for url in urls:
        print(f"  Fetching {url}")
        html = requests.get(url, headers=HEADERS, timeout=30).text
        time.sleep(6)  # Rate limit between requests
        all_games.extend(parse_season(html, season))
    
    games = all_games
    print(f"  Parsed {len(games)} games from season {season}")
    
    new_games_count = 0
    for game in games:
        # Parse game date
        try:
            game_date = Date.fromisoformat(game["date"])
        except (ValueError, KeyError):
            continue
        
        # Skip playoff games - only store regular season for now
        if playoffs_start and game_date >= playoffs_start:
            continue
            
        home_abbrev = game["home_team"]
        away_abbrev = game["away_team"]
        game_id = f"{home_abbrev}{away_abbrev}{season}{game['date'].replace('-', '')}"
        
        # Skip if already in DB (incremental mode)
        if incremental and game_id in existing_ids:
            continue
        
        # Skip games without scores (parse_season already filters, but double-check)
        if game["home_pts"] is None or game["away_pts"] is None:
            continue
        if game["home_pts"] == 0 and game["away_pts"] == 0:
            continue
            
        home_team_wins = game["home_pts"] > game["away_pts"]
        
        conn.execute("""
            INSERT OR IGNORE INTO games (game_id, home_team_id, away_team_id, game_date_est, season, home_team_points, away_team_points, home_team_wins)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            game_id, home_abbrev, away_abbrev, game["date"], season,
            game["home_pts"], game["away_pts"],
            home_team_wins
        ])
        new_games_count += 1
    
    conn.commit()
    count = conn.execute(f"SELECT COUNT(*) FROM games WHERE season = {season}").fetchone()[0]
    print(f"  Season {season}: inserted {new_games_count} NEW games (total: {count})")
    
    # Compute features for the season
    if new_games_count > 0:
        print(f"  Computing features for season {season}...")
        from nba_pickem.dataloader import recompute_features
        recompute_features(season)
        print(f"  Features computed!")
    
    conn.close()
    
    return new_games_count


def recompute_and_save(season: int):
    print(f"Recomputing features for season {season}...")
    from nba_pickem.dataloader import recompute_features
    recompute_features(season)
    print("Features computed!")


def load_all_seasons():
    conn = get_connection()
    conn.execute("DELETE FROM games")
    conn.commit()
    conn.close()
    
    for season in [2022, 2023, 2024, 2025, 2026]:
        load_season(season, force=True)


def main():
    parser = argparse.ArgumentParser(description="Load NBA data from Basketball-Reference")
    parser.add_argument("--teams", action="store_true", help="Load teams and aliases")
    parser.add_argument("--season", type=int, help="Load specific season (e.g., 2025)")
    parser.add_argument("--all-seasons", action="store_true", help="Load all seasons (2022-2026)")
    parser.add_argument("--force", action="store_true", help="Force reload (deletes existing)")
    parser.add_argument("--no-incremental", action="store_true", help="Load all games, not just new ones")
    parser.add_argument("--compute-features", action="store_true", help="Recompute features after loading")
    args = parser.parse_args()
    
    incremental = not args.no_incremental
    
    if args.teams:
        load_team_aliases()
        load_teams()
    elif args.all_seasons:
        load_all_seasons()
        if args.compute_features:
            recompute_and_save()
    elif args.season:
        new_count = load_season(args.season, force=args.force, incremental=incremental)
        if new_count > 0 and args.compute_features:
            recompute_and_save()
        # Update seasons table
        from nba_pickem.dataloader import update_season_games_count
        update_season_games_count(args.season)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()