import logging
import scrapy
import pandas as pd
from dao import retrieve_moneylines_df, retrieve_games_df, retrieve_teams_df

SPORTSBOOKS = [
    "fanduel",
    "mgm",
    "draftkings",
    "caesars",
    "rivers"
]


class BaseSportsBookScraper(scrapy.Spider):
    download_delay = 0.25
    allowed_domains = ["sportsbookreview.com"]
    start_urls = ["https://sportsbookreview.com"]

    def __init__(self, sportsbooks=SPORTSBOOKS):
        self.log(f"initializing {self.name}", level=logging.INFO)
        self.teams = retrieve_teams_df()
        self.nba_games = retrieve_games_df().sort_values(by="GAME_DATE_EST")
        self.odds = self._odds_df()
        self.sportsbooks=sportsbooks.split(',') if type(sportsbooks) == str else sportsbooks
        if len(self.odds) > 0:
            self.odds = self.odds.sort_values(by="GAME_DATE_EST")[self.odds['SPORTSBOOK'].isin(self.sportsbooks)]

        super().__init__()

    def start_requests(self):
        self.nba_games = self.nba_games[self.nba_games["SEASON"] >= 2019]
        if len(self.odds) > 0:
            self.nba_games = self.nba_games[~self.nba_games["GAME_DATE_EST"].isin(self.odds["GAME_DATE_EST"].unique())]

        game_dates = self.nba_games["GAME_DATE_EST"].unique()
        for game_date in game_dates:
            url = self._odds_url(game_date)
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        date = response.url.split("=")[-1]
        odds_rows = response.css("#tbody-nba > div.flex-row")
        sportsbook_cols = response.css("#thead-nba > div.d-flex.col-9 .sticky-sportbook").getall()
        sportsbook_to_column = {sportsbook: next(i for i, v in enumerate(sportsbook_cols) if sportsbook in v.lower()) for sportsbook in self.sportsbooks}

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
            for sportsbook in self.sportsbooks:
                if len(self.odds[(self.odds["GAME_ID"] == base_game["GAME_ID"]) & (self.odds["SPORTSBOOK"] == sportsbook)]):
                    continue
                sportsbook_col = sportsbook_to_column[sportsbook]
                away_odds, home_odds = self.parse_odds(row, sportsbook_col)
                if not pd.isna(away_odds) and not pd.isna(home_odds):
                    row_df = {**base_game, "AWAY_ODDS": away_odds, "HOME_ODDS": home_odds, "SPORTSBOOK": sportsbook}
                    games.append(row_df)
                else:
                    self.log(f"Game {base_game['GAME_ID']} on {base_game['GAME_DATE_EST']} has no odds for sportsbook: {sportsbook}", level=logging.INFO)
                    
        return games

    def parse_odds(self, odds_row, sportsbook_col):
        away_odds, home_odds = odds_row.css("div.col-10 > div > div > div > div")[sportsbook_col].xpath('.//span/span[2]/text()').getall()
        if not away_odds or not home_odds or away_odds == "-" or home_odds == "-":
            return (pd.NA, pd.NA)
        return (int(away_odds), int(home_odds))

    def translate_city(self, city):
        if city.startswith("L.A."):
            nickname = city.split(" ")[1]
            team = self.teams[self.teams["NICKNAME"] == nickname]
            return team["TEAM_ID"].values[0]
        else:
            team = self.teams[self.teams["CITY"] == city]
            return team["TEAM_ID"].values[0]

    def _odds_df(self):
        raise NotImplementedError()

    def _odds_url(self, game_date):
        raise NotImplementedError()
