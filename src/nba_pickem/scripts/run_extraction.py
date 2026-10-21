#!/usr/bin/env python3
"""NBA Pick'em - Data Extraction Script

Smart extraction that:
- Checks if season is complete → skips if yes
- Loads teams if not loaded
- Loads NEW games incrementally (skips existing, skips no scores)
- Recomputes features for new games
- Marks a season complete once its playoffs have started (works for shortened seasons)

Usage:
    nba-pickem-extract --teams     # Load teams only
    nba-pickem-extract            # Auto-detect latest incomplete season
    nba-pickem-extract --all      # All incomplete seasons
    nba-pickem-extract 2025       # Specific season
    nba-pickem-extract --since 2015  # Backfill every incomplete season from 2015 to now
"""
import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from nba_pickem.dataloader import (
    ensure_season,
    get_connection,
    has_teams,
    get_incomplete_seasons,
    get_current_season,
    update_season_games_count,
    update_season_completion,
    seed_seasons_from_games,
)
from nba_pickem.features import season_for_date

from nba_pickem.scripts.load_bball_ref_data import load_teams, load_team_aliases, load_season


def load_teams_if_needed():
    """Load teams if not already loaded."""
    if has_teams():
        print("Teams already loaded - skipping")
        return False
    
    print("Loading teams...")
    load_team_aliases()
    load_teams()
    return True


def extract_season(season: int, force: bool = False) -> bool:
    """Extract games for a specific season.
    
    Returns:
        True if new games were loaded, False otherwise
    """
    print(f"\n=== Extracting season {season} ===")
    
    conn = get_connection()
    result = conn.execute("""
        SELECT is_regular_season_complete, games_loaded 
        FROM seasons WHERE season_year = ?
    """, [season]).fetchone()
    
    conn.close()
    if result and result[0]:  # is_complete
        print(f"Season {season} is marked complete - skipping")
        return False
    
    # Load teams first if needed
    load_teams_if_needed()
    
    # Load games incrementally (recomputes features when games gain results)
    new_games = load_season(season, force=force)
    print(f"Loaded {new_games} NEW games for season {season}")
    
    update_season_games_count(season)
    update_season_completion(season)
    
    return new_games > 0


def extract_current():
    """Extract for the current (most recent incomplete) season."""
    current_season = get_current_season()
    
    if current_season is None:
        print("No incomplete seasons found. All seasons appear complete!")
        print("Run with --all to check all seasons, or specify a season manually.")
        return False
    
    print(f"Found current incomplete season: {current_season}")
    return extract_season(current_season)


def extract_all():
    """Extract for all incomplete seasons."""
    seasons = get_incomplete_seasons()
    
    if not seasons:
        print("No incomplete seasons found!")
        return False
    
    print(f"Found {len(seasons)} incomplete season(s): {seasons}")
    
    any_loaded = False
    for season in seasons:
        if extract_season(season):
            any_loaded = True
    
    return any_loaded


def extract_since(first_season: int):
    """Extract every incomplete season from first_season through the current one."""
    current = season_for_date(pd.Timestamp(datetime.now(ZoneInfo('US/Eastern')).date()))
    for season in range(first_season, current + 1):
        ensure_season(season)
        extract_season(season)


def seed_seasons():
    """Seed seasons table from existing games data."""
    print("Seeding seasons table from games data...")
    seed_seasons_from_games()
    print("Done!")


def main():
    parser = argparse.ArgumentParser(description="Extract NBA Pick'em data")
    parser.add_argument("--teams", action="store_true", help="Load teams only")
    parser.add_argument("--all", action="store_true", help="Extract all incomplete seasons")
    parser.add_argument("--force", action="store_true", help="Force reload (deletes existing)")
    parser.add_argument("--seed", action="store_true", help="Seed seasons table from games")
    parser.add_argument("--since", type=int, help="Extract all incomplete seasons from this one to now")
    parser.add_argument("season", nargs="?", type=int, help="Specific season (e.g., 2025)")
    args = parser.parse_args()
    
    # Seed seasons first if needed (or always to keep in sync)
    try:
        seed_seasons()
    except Exception as e:
        print(f"Note: Could not seed seasons: {e}")
    
    if args.teams:
        load_teams_if_needed()
        return
    
    if args.season:
        extract_season(args.season, force=args.force)
        return
    
    if args.since:
        extract_since(args.since)
        return
    
    if args.all:
        extract_all()
        return
    
    # Default: extract current season
    extract_current()


if __name__ == "__main__":
    main()