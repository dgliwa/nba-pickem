#!/usr/bin/env python3
"""Setup script for NBA Pick'em.

Initializes the DuckDB database and optionally loads seed data.

Usage:
    nba-pickem-init           # Initialize empty DB
    nba-pickem-init --load  # Initialize and load seed data from CSV
"""
import argparse

from nba_pickem.config import DATA_DIR
from nba_pickem.dataloader import init_db, get_teams, save_teams, get_games, save_games


def load_seed_data():
    print("Loading seed data...")

    teams_csv = DATA_DIR / "raw" / "nba_teams.csv"
    if teams_csv.exists():
        import pandas as pd
        teams_df = pd.read_csv(teams_csv)
        if not teams_df.empty:
            save_teams(teams_df)
            print(f"Loaded {len(teams_df)} teams")

    games_csv = DATA_DIR / "raw" / "nba_games.csv"
    if games_csv.exists():
        import pandas as pd
        games_df = pd.read_csv(games_csv, parse_dates=["GAME_DATE_EST"])
        if not games_df.empty:
            save_games(games_df)
            print(f"Loaded {len(games_df)} games")

    print("Seed data load complete!")


def main():
    parser = argparse.ArgumentParser(description="Setup NBA Pick'em database")
    parser.add_argument("--load", action="store_true", help="Load seed data from CSV files")
    args = parser.parse_args()

    print("Initializing database...")
    init_db()
    print("Database initialized!")

    if args.load:
        load_seed_data()


if __name__ == "__main__":
    main()