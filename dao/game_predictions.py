import os
import pandas as pd
from dao.db import engine as db_engine
from sqlalchemy import text


def retrieve_game_predictions_df(game_date) -> pd.DataFrame:
    if db_engine:
        with db_engine.connect() as con:
            query = f"""
                SELECT
                gp.GAME_ID,
                gp.HOME_TEAM_ID,
                gp.AWAY_TEAM_ID,
                gp.GAME_DATE_EST,
                gp.PREDICTED_HOME_TEAM_WINS,
                g.HOME_TEAM_POINTS,
                g.AWAY_TEAM_POINTS,
                gp.HOME_WIN_PCT,
                gp.HOME_HOME_WIN_PCT,
                gp.AWAY_WIN_PCT,
                gp.AWAY_AWAY_WIN_PCT,
                gp.HOME_LAST_10_WIN_PCT,
                gp.AWAY_LAST_10_WIN_PCT,
                gp.HOME_TEAM_B2B,
                gp.AWAY_TEAM_B2B,
                g.HOME_TEAM_WINS,
                mo.HOME_ODDS,
                mo.AWAY_ODDS
                FROM GAME_PREDICTIONS gp
                LEFT JOIN GAMES g ON gp.GAME_ID = g.GAME_ID
                LEFT JOIN MONEYLINE_ODDS mo ON mo.ID = (SELECT id from MONEYLINE_ODDS WHERE sportsbook = 'fanduel' AND GAME_ID = gp.GAME_ID ORDER BY line_datetime DESC LIMIT 1)
                WHERE gp.GAME_DATE_EST = '{game_date.strftime('%Y-%m-%d')}'
            """
            df = pd.read_sql(query, con)
            df.columns = [c.upper() for c in df.columns]
            df["HOME_TEAM_ID"] = df["HOME_TEAM_ID"].astype(int)
            df["AWAY_TEAM_ID"] = df["AWAY_TEAM_ID"].astype(int)
            return df
    elif os.path.exists("data/raw/nba_game_predictions.csv"):
        return pd.read_csv("data/raw/nba_game_predictions.csv", dtype={"GAME_ID": str}, parse_dates=["GAME_DATE_EST"])
    else:
        return pd.DataFrame()


def save_game_predictions_df(game_predictions_df):
    game_predictions_df.drop_duplicates(inplace=True, subset=["GAME_ID"])
    if db_engine:
        game_predictions_df = game_predictions_df[[
            "GAME_ID",
            "HOME_TEAM_ID",
            "AWAY_TEAM_ID",
            "PREDICTION",
            "GAME_DATE_EST",
            "HOME_WIN_PCT",
            "HOME_HOME_WIN_PCT",
            "AWAY_WIN_PCT",
            "AWAY_AWAY_WIN_PCT",
            "HOME_TEAM_B2B",
            "AWAY_TEAM_B2B",
            "HOME_LAST_10_WIN_PCT",
            "AWAY_LAST_10_WIN_PCT"
        ]]
        game_predictions_df = game_predictions_df.rename({"PREDICTION": "PREDICTED_HOME_TEAM_WINS"}, axis=1)
        with db_engine.connect() as con:
            game_predictions_df.columns = [c.lower() for c in game_predictions_df.columns]
            game_predictions_df.to_sql('game_predictions', con=con, if_exists='append', index=False)
    else:
        if not os.path.exists("data/raw/nba_game_predictions.csv"):
            game_predictions_df.to_csv("data/raw/nba_game_predictions.csv", index=False)
        else:
            game_predictions_df.to_csv("data/raw/nba_game_predictions.csv", index=False, mode="a", header=False)


def retrieve_game_predictions_with_results(bet_amount):
    if db_engine:
        with db_engine.connect() as con:
            query = f"""
            SELECT
            SUM(CASE WHEN gp.predicted_home_team_wins = g.home_team_wins THEN 1 ELSE 0 END) as CORRECT_PREDICTIONS,
            SUM(
                CASE WHEN gp.predicted_home_team_wins AND g.home_team_wins
                    THEN
                        CASE WHEN mo.HOME_ODDS IS NULL THEN 0
                        WHEN mo.HOME_ODDS < 0 THEN {bet_amount} * (100.0 / ABS(mo.HOME_ODDS))
                        ELSE {bet_amount} * (mo.HOME_ODDS / 100.0) END
                WHEN NOT gp.predicted_home_team_wins AND NOT g.home_team_wins
                    THEN
                        CASE WHEN mo.AWAY_ODDS IS NULL THEN 0
                        WHEN mo.AWAY_ODDS < 0 THEN {bet_amount} * (100.0 / ABS(mo.AWAY_ODDS))
                        ELSE {bet_amount} * (mo.AWAY_ODDS / 100.0) END
                ELSE
                    -{bet_amount}
                END
            ) as PREDICTED_WINNINGS,
            SUM(
                CASE WHEN (gp.predicted_home_team_wins AND g.home_team_wins AND mo.HOME_ODDS > 0) OR (NOT gp.predicted_home_team_wins AND NOT g.home_team_wins AND mo.AWAY_ODDS > 0)
                    THEN 1
                    ELSE 0
                    END
     
            ) as AGAINST_MONEYLINE_FAVORITE,
            COUNT(*) as TOTAL_GAMES
            FROM game_predictions gp
            JOIN games g ON gp.game_id = g.game_id
            LEFT JOIN MONEYLINE_ODDS mo ON mo.ID = (SELECT id from MONEYLINE_ODDS WHERE sportsbook = 'fanduel' AND GAME_ID = gp.GAME_ID ORDER BY line_datetime DESC LIMIT 1)
            WHERE g.season = 2024
            """
            results = con.execute(text(query))
            correct_predictions, predicted_winnings, against_moneyline_favorite, total_games = results.one()
            return {
                "correct_predictions": correct_predictions,
                "predicted_winnings": predicted_winnings,
                "against_moneyline_favorite": against_moneyline_favorite,
                "total_games": total_games
            }
    else:
        return {"correct_predictions": 0, "total_games": 0}
