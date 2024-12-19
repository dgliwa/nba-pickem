import scrapy

import logging
import pandas as pd
from datetime import datetime

class NbaSeasonMatchupsSpider(scrapy.Spider):
    download_delay = 0.25
    name = "nba_season_matchups"
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
        teams = pd.read_csv("data/teams.csv")

        most_recent_season = self.STARTING_YEAR
        for season in range(most_recent_season, datetime.now().year):
            for team_id in teams["TEAM_ID"]:
                formatted_season = self.convert_to_season_format(season)
                url = f"https://stats.nba.com/stats/cumestatsteamgames?LeagueID=00&Season={formatted_season}&SeasonType=Regular+Season&TeamID={team_id}"
                yield scrapy.Request(url=url, headers=self.HEADERS, callback=self.build_callback(team_id, season))

    def build_callback(self, team_id, season):
        return lambda r: self.parse(team_id, season, r)


    def parse(self, team_id, year, response):
        jsonresponse = response.json()
        if len(jsonresponse.get("resultSets")[0].get("rowSet")) != 82:
            self.log(f"Team {team_id} did not play 82 games in {year}", level=logging.INFO)

        games = []
        for row in jsonresponse.get("resultSets")[0].get("rowSet"):
            games.append({ "SEASON": year, "GAME_ID": row[1], "TEAM_ID": team_id })
        return games

    def convert_to_season_format(self, season):
        return f"{season}-{(season % 2000) + 1}"

