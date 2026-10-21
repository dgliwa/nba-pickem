"""Integration check: prediction-time features must reproduce training-time features."""
import pandas as pd
import pytest

from nba_pickem.config import DB_PATH
from nba_pickem.dataloader import get_games
from nba_pickem.features import ROLLING_FEATURES, add_matchup_diffs, matchup_features, season_for_date

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="requires local DuckDB")


def test_prediction_features_match_stored_training_features():
    games = get_games(played_only=True)
    sample = add_matchup_diffs(games[games['season'] == 2026]).sample(60, random_state=0)

    for _, game in sample.iterrows():
        prior = games[
            (games['game_date_est'] < game['game_date_est'])
            & (games['season'] == season_for_date(game['game_date_est']))
        ]
        rebuilt = add_matchup_diffs(pd.DataFrame([matchup_features(prior, game['home_team_id'], game['away_team_id'])]))
        for col in ROLLING_FEATURES:
            assert rebuilt[col].iloc[0] == pytest.approx(float(game[col]), abs=0.02), (game['game_id'], col)
