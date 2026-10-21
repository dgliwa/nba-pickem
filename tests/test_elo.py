import pandas as pd
import pytest

from nba_pickem.features import ELO_START, compute_elo


def game(game_id, date, season, home, away, home_pts=None, away_pts=None):
    played = home_pts is not None
    return {"game_id": game_id, "game_date_est": pd.Timestamp(date), "season": season,
            "home_team_id": home, "away_team_id": away, "home_team_points": home_pts,
            "away_team_points": away_pts, "home_team_wins": (home_pts > away_pts) if played else None}


def elo_by_id(games):
    return compute_elo(pd.DataFrame(games)).set_index('game_id')


def test_winner_gains_what_loser_loses():
    elo = elo_by_id([game("g1", "2024-10-22", 2025, "BOS", "NYK", 110, 100),
                     game("g2", "2024-10-24", 2025, "BOS", "NYK", 100, 101)])
    assert (elo.loc["g1", "home_elo_pre"], elo.loc["g1", "away_elo_pre"]) == (ELO_START, ELO_START)
    bos, nyk = elo.loc["g2", "home_elo_pre"], elo.loc["g2", "away_elo_pre"]
    assert bos > ELO_START > nyk
    assert bos + nyk == pytest.approx(2 * ELO_START)


def test_ratings_regress_toward_mean_between_seasons():
    elo = elo_by_id([game("g1", "2024-04-10", 2024, "BOS", "NYK", 130, 90),
                     game("g2", "2024-04-12", 2024, "BOS", "NYK"),
                     game("g3", "2024-10-22", 2025, "BOS", "NYK")])
    end_of_season = elo.loc["g2", "home_elo_pre"]
    assert elo.loc["g3", "home_elo_pre"] - ELO_START == pytest.approx(0.75 * (end_of_season - ELO_START))


def test_unplayed_games_get_current_ratings_without_updating_them():
    elo = elo_by_id([game("g1", "2024-10-22", 2025, "BOS", "NYK", 110, 100),
                     game("g2", "2024-10-24", 2025, "BOS", "NYK"),
                     game("g3", "2024-10-26", 2025, "BOS", "NYK")])
    assert elo.loc["g2"].tolist() == elo.loc["g3"].tolist()
    assert elo.loc["g2", "home_elo_pre"] > ELO_START
