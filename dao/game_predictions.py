import os
import pandas as pd
from dao.db import engine as db_engine
from sqlalchemy import text


def retrieve_game_predictions_df() -> pd.DataFrame:
    if db_engine:
        with db_engine.connect() as con:
            query = """
                SELECT
                GAME_ID,
                HOME_TEAM_ID,
                AWAY_TEAM_ID,
                GAME_DATE_EST,
                PREDICTED_HOME_TEAM_WINS
                FROM GAME_PREDICTIONS
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
        game_predictions_df = game_predictions_df[["GAME_ID", "HOME_TEAM_ID", "AWAY_TEAM_ID", "PREDICTION", "GAME_DATE_EST"]]
        game_predictions_df = game_predictions_df.rename({"PREDICTION": "PREDICTED_HOME_TEAM_WINS"}, axis=1)
        with db_engine.connect() as con:
            game_predictions_df.columns = [c.lower() for c in game_predictions_df.columns]
            game_predictions_df.to_sql('game_predictions', con=con, if_exists='append', index=False)
    else:
        if not os.path.exists("data/raw/nba_game_predictions.csv"):
            game_predictions_df.to_csv("data/raw/nba_game_predictions.csv", index=False)
        else:
            game_predictions_df.to_csv("data/raw/nba_game_predictions.csv", index=False, mode="a", header=False)


def retrieve_game_predictions_with_results():
    if db_engine:
        with db_engine.connect() as con:
            query = """
            SELECT
            SUM(CASE WHEN gp.predicted_home_team_wins = g.home_team_wins THEN 1 ELSE 0 END) as CORRECT_PREDICTIONS,
            COUNT(*) as TOTAL_GAMES
            FROM game_predictions gp
            JOIN games g ON gp.game_id = g.game_id
            WHERE g.season = 2024
            """
            results = con.execute(text(query))
            correct_predictions, total_games = results.one()
            return {"correct_predictions": correct_predictions, "total_games": total_games}
    else:
        return {"correct_predictions": 0, "total_games": 0}
