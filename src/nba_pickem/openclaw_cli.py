"""JSON interface used by the OpenClaw NBA Pick'em plugin."""

import argparse
import contextlib
import json
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from nba_pickem.dataloader import ensure_season, update_season_games_count
from nba_pickem.features import season_for_date
from nba_pickem.reporting import build_daily_report
from nba_pickem.scripts.load_bball_ref_data import load_season
from nba_pickem.scripts.run_prediction import predict_for_date


def execute_daily(report_date: date) -> dict:
    """Refresh the season, persist picks, and return a deterministic report."""
    season = season_for_date(pd.Timestamp(report_date))
    ensure_season(season)
    load_season(season)
    update_season_games_count(season)
    predict_for_date(report_date)
    return build_daily_report(report_date)


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw JSON bridge for NBA Pick'em")
    parser.add_argument("command", choices=("daily", "report"))
    parser.add_argument("--date", dest="report_date", help="Report date in YYYY-MM-DD format")
    args = parser.parse_args()
    report_date = date.fromisoformat(args.report_date) if args.report_date else datetime.now(ZoneInfo("US/Eastern")).date()

    if args.command == "daily":
        with contextlib.redirect_stdout(sys.stderr):
            report = execute_daily(report_date)
    else:
        report = build_daily_report(report_date)
    print(json.dumps(report, separators=(",", ":")))


if __name__ == "__main__":
    main()
