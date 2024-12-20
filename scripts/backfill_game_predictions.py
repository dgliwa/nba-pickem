from datetime import datetime, timedelta, date
import sys

from worker import predict_todays_games


def backfill_game_predictions(start_date, end_date):
    for single_date in _daterange(start_date, end_date):
        predict_todays_games.delay(single_date)


def _daterange(start_date: date, end_date: date):
    days = int((end_date - start_date).days)
    for n in range(days):
        yield start_date + timedelta(n)


if __name__ == "__main__":
    start_date_str, end_date_str = sys.argv[1:3]
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    backfill_game_predictions(start_date, end_date)
