#!/usr/bin/env python3
"""NBA Pick'em - Daily job

Syncs the current season from basketball-reference (fills in results for games played,
refreshes the schedule), refreshes recent moneyline odds, then predicts today's games.

Usage:
    nba-pickem-daily
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from nba_pickem.dataloader import ensure_season, update_season_games_count
from nba_pickem.features import season_for_date
from nba_pickem.scripts.load_bball_ref_data import load_season
from nba_pickem.scripts.load_odds import refresh_recent_odds
from nba_pickem.scripts.run_prediction import predict_for_date, print_predictions


def main():
    today = datetime.now(ZoneInfo('US/Eastern')).date()
    season = season_for_date(pd.Timestamp(today))

    ensure_season(season)
    load_season(season)
    update_season_games_count(season)
    refresh_recent_odds(today)

    print(f"\nPredictions for {today}:")
    predictions = predict_for_date(today)
    if predictions.empty:
        print("  No unplayed games today.")
    else:
        print_predictions(predictions)


if __name__ == "__main__":
    main()
