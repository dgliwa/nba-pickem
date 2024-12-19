import scrapy

import os

class NbaTeamsSpider(scrapy.Spider):
    download_delay = 0.25
    name = "nba_teams"
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
        if os.path.exists("data/raw/nba_teams.csv"):
            return

        url = "https://stats.nba.com/stats/commonteamyears?LeagueID=00"
        yield scrapy.Request(url=url, headers=self.HEADERS, callback=self.parse_teams)

    def parse_teams(self, response):
        jsonresponse = response.json()
        return [
            scrapy.Request(url=f"https://stats.nba.com/stats/teamdetails?TeamID={team[1]}", headers=self.HEADERS, callback=self.parse_team)
            for team in jsonresponse.get("resultSets")[0].get("rowSet")
        ]


    def parse_team(self, response):
        if not response.json().get("resultSets")[0].get("rowSet"):
            return
        team_background = response.json().get("resultSets")[0].get("rowSet")[0]

        return {
            "LEAGUE_ID": "00",
            "TEAM_ID": team_background[0],
            "ABBREVIATION": team_background[1],
            "NICKNAME": team_background[2],
            "YEARFOUNDED": team_background[3],
            "CITY": team_background[4],
            "ARENA": team_background[5],
            "ARENACAPACITY": team_background[6],
            "OWNER": team_background[7],
            "GENERALMANAGER": team_background[8],
            "HEADCOACH": team_background[9],
            "DLEAGUEAFFILIATION": team_background[10]
        }



