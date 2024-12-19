import scrapy

import os
import pandas as pd
from datetime import datetime

class NbaGamesSpider(scrapy.Spider):
    download_delay = 0.25
    name = "nba_games"
    allowed_domains = ["stats.nba.com"]
    start_urls = ["https://stats.nba.com"]

    HEADERS = {
        "Referer": "stats.nba.com",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Host": "stats.nba.com",
        "Origin": "https://stats.nba.com",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:70.0) Gecko/20100101 Firefox/70.0",
    }

    STARTING_YEAR = 2017

    def start_requests(self):
        matchups = pd.read_csv("data/nba_season_matchups.csv", dtype={"GAME_ID": str})

        if os.path.exists("data/nba_games.csv"):
            df = pd.read_csv("data/nba_games.csv", dtype={"GAME_ID": str})
            games = matchups[~(matchups["GAME_ID"].isin(df["GAME_ID"].unique()))]["GAME_ID"].unique()
        else:
            games = matchups["GAME_ID"].unique()


        for game in games:
            url = f"https://stats.nba.com/stats/boxscoresummaryv2?GameID={game}"
            yield scrapy.Request(url=url, headers=self.HEADERS, callback=self.build_callback(game))

    def build_callback(self, game):
        return lambda r: self.parse(game, r)


    def parse(self, game, response):
        jsonresponse = response.json()
        results = jsonresponse.get("resultSets")
        summary = results[0]
        game_date_est = summary.get("rowSet")[0][0]
        home_team_id = summary.get("rowSet")[0][6]
        away_team_id = summary.get("rowSet")[0][7]
        season = summary.get("rowSet")[0][8]
        line_score = results[5]
        home_line = 0 if line_score.get("rowSet")[0][5] == home_team_id else 1
        away_line = 1 if home_line == 0 else 0
        home_team_points = line_score.get("rowSet")[home_line][22]
        away_team_points = line_score.get("rowSet")[away_line][22]
        return {
            "GAME_DATE_EST": datetime.strptime(game_date_est, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d"),
            "GAME_ID": game,
            "HOME_TEAM_ID": home_team_id,
            "AWAY_TEAM_ID": away_team_id,
            "SEASON": season,
            "HOME_TEAM_POINTS": home_team_points,
            "AWAY_TEAM_POINTS": away_team_points,
            "HOME_TEAM_WINS": home_team_points > away_team_points,
        }
