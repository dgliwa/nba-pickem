import os
import pandas as pd
from dao.db import engine as db_engine


def retrieve_games_df() -> pd.DataFrame:
    if db_engine:
        with db_engine.connect() as con:
            query = """
        SELECT
          GAME_ID,
          HOME_TEAM_ID,
          AWAY_TEAM_ID,
          GAME_DATE_EST,
          SEASON,
          HOME_TEAM_POINTS,
          AWAY_TEAM_POINTS,
          HOME_WIN_PCT,
          HOME_HOME_WIN_PCT,
          AWAY_WIN_PCT,
          AWAY_AWAY_WIN_PCT,
          HOME_LAST_10_WIN_PCT,
          AWAY_LAST_10_WIN_PCT,
          HOME_TEAM_B2B,
          AWAY_TEAM_B2B,
          HOME_TEAM_WINS
        FROM GAMES
      """
            df = pd.read_sql(query, con)
            df.columns = [c.upper() for c in df.columns]
            df["HOME_TEAM_ID"] = df["HOME_TEAM_ID"].astype(int)
            df["AWAY_TEAM_ID"] = df["AWAY_TEAM_ID"].astype(int)
            return df
    elif os.path.exists("data/raw/nba_games.csv"):
        return pd.read_csv("data/raw/nba_games.csv", dtype={"GAME_ID": str}, parse_dates=["GAME_DATE_EST"])
    else:
        return pd.DataFrame()


def save_games_df(games_df):
    games_df.drop_duplicates(inplace=True, subset=["GAME_ID"])
    if db_engine:
        games_df = preprocess_games_df(games_df)
        with db_engine.connect() as con:
            games_df.columns = [c.lower() for c in games_df.columns]
            games_df.to_sql('games', con=con, if_exists='append', index=False)
    else:
        if not os.path.exists("data/raw/nba_games.csv"):
            games_df.to_csv("data/raw/nba_games.csv", index=False)
        else:
            games_df.to_csv("data/raw/nba_games.csv",
                            index=False, mode="a", header=False)


def preprocess_games_df(games_df):
    games_df["GAME_DATE_EST"] = pd.to_datetime(games_df["GAME_DATE_EST"])
    existing_games = retrieve_games_df()
    games_superset = pd.concat([games_df, existing_games]).drop_duplicates(
        subset=["GAME_ID"]).sort_values(by="GAME_DATE_EST")
    games_superset["GAME_DATE_EST"] = pd.to_datetime(
        games_superset["GAME_DATE_EST"])

    games_df = _calculate_b2bs(games_df, games_superset)
    games_df = _calculate_game_lookback_data(games_df, games_superset)
    return games_df


def _calculate_b2bs(games_df, games_superset):
    games_df[["HOME_TEAM_B2B", "AWAY_TEAM_B2B"]] = games_df.apply(
        lambda game: _get_b2bs(game, games_superset), axis=1)
    return games_df


def _get_b2bs(game, games_superset):
    date = game['GAME_DATE_EST'] - pd.Timedelta(days=1)
    home_team = game['HOME_TEAM_ID']
    away_team = game['AWAY_TEAM_ID']
    home_b2b = len(games_superset.loc[(games_superset['GAME_DATE_EST'] == date) & (
        (games_superset['HOME_TEAM_ID'] == home_team) | (games_superset['AWAY_TEAM_ID'] == home_team))])
    away_b2b = len(games_superset.loc[(games_superset['GAME_DATE_EST'] == date) & (
        (games_superset['HOME_TEAM_ID'] == away_team) | (games_superset['AWAY_TEAM_ID'] == away_team))])
    return pd.Series([bool(home_b2b), bool(away_b2b)])


def _calculate_game_lookback_data(games_df, games_superset):
    return pd.concat(games_df.sort_values(by="GAME_DATE_EST").apply(lambda row: _get_game_lookback_data(row, games_superset), axis=1).to_list())


def _get_game_lookback_data(game, games_superset):
    home_team_id = game['HOME_TEAM_ID']
    home_last_10_win_pct = _get_last_n_win_pct(
        home_team_id, 10, games_superset)
    home_last_10_win_pct = home_last_10_win_pct[home_last_10_win_pct["GAME_ID"]
                                                == game["GAME_ID"]]
    home_last_10_win_pct.drop(columns="GAME_ID", inplace=True)
    home_lookback_data = pd.concat(
        [home_last_10_win_pct], axis=1).add_prefix('HOME_')

    away_team_id = game['AWAY_TEAM_ID']
    away_last_10_win_pct = _get_last_n_win_pct(
        away_team_id, 10, games_superset)
    away_last_10_win_pct = away_last_10_win_pct[away_last_10_win_pct["GAME_ID"]
                                                == game["GAME_ID"]]
    away_last_10_win_pct.drop(columns="GAME_ID", inplace=True)
    away_lookback_data = pd.concat(
        [away_last_10_win_pct], axis=1).add_prefix('AWAY_')

    lookback_data = pd.concat(
        [game.to_frame().T, home_lookback_data, away_lookback_data], axis=1)
    lookback_data["HOME_TEAM_WINS"] = lookback_data["HOME_TEAM_WINS"].astype(
        bool)
    return lookback_data


def _get_last_n_win_pct(team_id, n, games):
    _game = games[(games['HOME_TEAM_ID'] == team_id) |
                  (games['AWAY_TEAM_ID'] == team_id)]
    _game.loc[:, 'IS_HOME'] = _game['HOME_TEAM_ID'] == team_id
    _game.loc[:, 'WIN_PRCT'] = _game['IS_HOME'] == _game['HOME_TEAM_WINS']
    rolling_win_pct = _game["WIN_PRCT"].rolling(
        n, min_periods=1).mean().rename(f"LAST_{n}_WIN_PCT")
    return pd.concat([_game["GAME_ID"], rolling_win_pct], axis=1)
