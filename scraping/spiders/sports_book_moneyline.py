import logging
import scrapy
import pandas as pd
from dao import retrieve_moneylines_df, retrieve_games_df, retrieve_teams_df

SPORTSBOOKS = [
    "fanduel",
    "mgm",
    "draftkings",
    "caesars"
]


class SportsBookMoneylineSpider(scrapy.Spider):
    download_delay = 0.25
    name = "sports_book_moneyline"
    allowed_domains = ["sportsbookreview.com"]
    start_urls = ["https://sportsbookreview.com"]

    def __init__(self):
        self.log("initializing moneylines spider", level=logging.INFO)
        self.teams = retrieve_teams_df()
        self.nba_games = retrieve_games_df().sort_values(by="GAME_DATE_EST")
        self.moneylines = retrieve_moneylines_df()
        if len(self.moneylines) > 0:
            self.moneylines = self.moneylines.sort_values(by="GAME_DATE_EST")

        super().__init__()

    def start_requests(self):
        self.nba_games = self.nba_games[self.nba_games["SEASON"] >= 2019]
        if len(self.moneylines) > 0:
            self.nba_games = self.nba_games[~self.nba_games["GAME_DATE_EST"].isin(self.moneylines["GAME_DATE_EST"].unique())]

        game_dates = self.nba_games["GAME_DATE_EST"].unique()
        for game_date in game_dates:
            url = f"https://www.sportsbookreview.com/betting-odds/nba-basketball/money-line/full-game/?date={game_date.strftime('%Y-%m-%d')}"
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        date = response.url.split("=")[-1]
        odds_rows = response.css("#tbody-nba > div.flex-row")

        games = []
        for row in odds_rows:
            participants = row.xpath(".//span[re:test(@class, 'participant')]/text()")
            base_game = {"GAME_DATE_EST": date}

            away_city, home_city = [p.get().strip() for p in participants]
            away_team_id = self.translate_city(away_city)
            home_team_id = self.translate_city(home_city)

            clause = (
                (self.nba_games["HOME_TEAM_ID"] == home_team_id) &
                (self.nba_games["AWAY_TEAM_ID"] == away_team_id) &
                (self.nba_games["GAME_DATE_EST"] == date)
            )
            matching_games = self.nba_games[clause]
            if len(matching_games) != 1:
                self.log(f"FOUND WRONG NUMBER OF GAMES: {len(matching_games)}", level=logging.INFO)
                continue

            base_game.update({"GAME_ID": matching_games["GAME_ID"].values[0]})
            for sportsbook in SPORTSBOOKS:
                away_odds, home_odds = self.parse_odds(sportsbook, row)
                if not pd.isna(away_odds) and not pd.isna(home_odds):
                    row_df = {**base_game, "AWAY_ODDS": away_odds, "HOME_ODDS": home_odds, "SPORTSBOOK": sportsbook}
                    games.append(row_df)
        return games

    def parse_odds(self, sportsbook, odds_row):
        odds = odds_row.xpath(f".//a[re:test(@href, '{sportsbook}')]/div/div/span[@role='button']/span[2]/text()")
        if not odds:
            self.log(f"No odds for sportsbook: {sportsbook}", level=logging.INFO)
            return (pd.NA, pd.NA)
        return (int(odds[0].get()), int(odds[1].get()))

    def translate_city(self, city):
        if city.startswith("L.A."):
            nickname = city.split(" ")[1]
            team = self.teams[self.teams["NICKNAME"] == nickname]
            return team["TEAM_ID"].values[0]
        else:
            team = self.teams[self.teams["CITY"] == city]
            return team["TEAM_ID"].values[0]
