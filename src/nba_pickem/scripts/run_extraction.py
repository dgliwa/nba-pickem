#!/usr/bin/env python3
"""NBA Pick'em - Data Extraction Script

Smart extraction that:
- Checks if season is complete → skips if yes
- Loads teams if not loaded
- Loads NEW games incrementally (skips existing, skips no scores)
- Recomputes features for new games
- Marks season complete when 1200+ games loaded AND no new games

Usage:
    nba-pickem-extract --teams     # Load teams only
    nba-pickem-extract            # Auto-detect latest incomplete season
    nba-pickem-extract --all      # All incomplete seasons
    nba-pickem-extract 2025       # Specific season
"""
import argparse
import sys

from nba_pickem.dataloader import (
    get_connection,
    has_teams,
    get_incomplete_seasons,
    get_current_season,
    update_season_games_count,
    mark_season_complete,
    get_season_games_count,
    seed_seasons_from_games,
    recompute_features,
)

from nba_pickem.scripts.load_bball_ref_data import load_teams, load_team_aliases, load_season


MIN_REGULAR_SEASON_GAMES = 1200


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
    
    if result and result[0]:  # is_complete
        print(f"Season {season} is marked complete - skipping")
        return False
    
    conn.close()
    
    # Load teams first if needed
    load_teams_if_needed()
    
    # Load games incrementally
    new_games = load_season(season, force=force, incremental=True)
    print(f"Loaded {new_games} NEW games for season {season}")
    
    # Update games count in seasons table
    update_season_games_count(season)
    
    # Check if we should mark complete
    total_games = get_season_games_count(season)
    if total_games >= MIN_REGULAR_SEASON_GAMES and new_games == 0:
        print(f"Season {season} appears complete ({total_games} games, no new games)")
        mark_season_complete(season)
    elif total_games >= MIN_REGULAR_SEASON_GAMES:
        print(f"Season {season} has {total_games} games but checking for more...")
    
    # Recompute features if new games loaded
    if new_games > 0:
        print("Recomputing features for new games...")
        recompute_features()
    
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
    
    if args.all:
        extract_all()
        return
    
    # Default: extract current season
    extract_current()


if __name__ == "__main__":
    main()