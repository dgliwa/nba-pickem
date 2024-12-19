import os
import pandas as pd
from dao.db import engine as db_engine


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
