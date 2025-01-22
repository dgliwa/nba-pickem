import os
import pandas as pd
from dao.db import engine as db_engine


def retrieve_moneylines_df() -> pd.DataFrame:
    if db_engine:
        with db_engine.connect() as con:
            df = pd.read_sql('SELECT GAME_ID, SPORTSBOOK, HOME_ODDS, AWAY_ODDS, GAME_DATE_EST FROM MONEYLINE_ODDS', con)
            df.columns = [c.upper() for c in df.columns]

            return df.sort_values(by="GAME_DATE_EST")
    elif os.path.exists("data/raw/odds/moneylines.csv"):
        return pd.read_csv("data/raw/odds/moneylines.csv", dtype={"GAME_ID": str}, parse_dates=["GAME_DATE_EST"]).sort_values(by="GAME_DATE_EST")
    else:
        return pd.DataFrame()


def save_moneylines_df(moneylines_df):
    moneylines_df.drop_duplicates(inplace=True, subset=["GAME_ID", "SPORTSBOOK"]) 
    if db_engine:
        with db_engine.connect() as con:
            moneylines_df.columns = [c.lower() for c in moneylines_df.columns]
            moneylines_df.to_sql('moneyline_odds', con=con, if_exists='append', index=False)
    else:
        if not os.path.exists("data/raw/odds/moneylines.csv"):
            moneylines_df.to_csv("data/raw/odds/moneylines.csv", index=False)
        else:
            moneylines_df.to_csv("data/raw/odds/moneylines.csv", index=False, mode="a", header=False)
