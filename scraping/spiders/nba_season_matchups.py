import scrapy

import logging
from datetime import datetime
from scraping.data import retrieve_matchups_df, retrieve_teams_df

class NbaSeasonMatchupsSpider(scrapy.Spider):
    download_delay = 0.75
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

    STARTING_YEAR = 2024
    # STARTING_YEAR = 2017

    def __init__(self):
        self.log("initializing nba season matchups spider", level=logging.INFO)
        self.matchups = retrieve_matchups_df()

        self.teams = retrieve_teams_df()
        super().__init__()

    def start_requests(self):
        most_recent_season = self.STARTING_YEAR
        if len(self.matchups) > 0:
            most_recent_season = self.matchups["SEASON"].max()

        for season in range(most_recent_season, datetime.now().year + 1):
            for team_id in self.teams["TEAM_ID"]:
                formatted_season = self.convert_to_season_format(season)
                url = f"https://stats.nba.com/stats/cumestatsteamgames?LeagueID=00&Season={formatted_season}&SeasonType=Regular+Season&TeamID={team_id}"
                yield scrapy.Request(url=url, headers=self.HEADERS, callback=self.build_callback(team_id, season))

    def build_callback(self, team_id, season):
        return lambda r: self.parse(team_id, season, r)

    def parse(self, team_id, year, response):
        jsonresponse = response.json()
        if len(jsonresponse.get("resultSets")[0].get("rowSet")) != 82:
            self.log(f"Team {team_id} did not play 82 games in {year}", level=logging.INFO)

        matchups = []
        for row in jsonresponse.get("resultSets")[0].get("rowSet"):
            date = row[0].split()[0]
            game_date = datetime.strptime(date, "%m/%d/%Y")
            if game_date.date() == datetime.today().date() or (len(self.matchups) > 0 and row[1] in self.matchups["GAME_ID"].values):
                continue
            game_date_str = game_date.strftime("%Y-%m-%d")
            matchups.append({ "SEASON": year, "GAME_ID": row[1], "GAME_DATE_EST": game_date_str })
        return matchups

    def convert_to_season_format(self, season):
        return f"{season}-{(season % 2000) + 1}"

