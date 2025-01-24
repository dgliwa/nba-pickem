import logging
import scrapy
import json
from dao import retrieve_games_df, retrieve_teams_df
from datetime import datetime
from zoneinfo import ZoneInfo

SPORTSBOOKS = {
    "fanduel": "fanduel",
    "mgm": "betmgm",
    "draftkings": "draftkings",
    "caesars": "caesars",
    "rivers": "bet_rivers_ny",
    "bet365": "bet365",
}


class BaseSportsBookScraper(scrapy.Spider):
    download_delay = 0.25
    allowed_domains = ["sportsbookreview.com"]
    start_urls = ["https://sportsbookreview.com"]

    def __init__(self, sportsbooks=SPORTSBOOKS.values()):
        self.log(f"initializing {self.name}", level=logging.INFO)
        self.teams = retrieve_teams_df()
        self.nba_games = retrieve_games_df().sort_values(by="GAME_DATE_EST")
        self.odds = self._odds_df()
        self.sportsbooks=[SPORTSBOOKS[s] for s in sportsbooks.split(',') if s in SPORTSBOOKS] if type(sportsbooks) == str else sportsbooks
        self.log(f"Pulling odds for {self.sportsbooks}")
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
        
        line_data_links = response.xpath(".//a[@data-cy='button-grid-linehistory']/@href").getall()
        for link in line_data_links:
                yield scrapy.Request(url=f"https://sportsbookreview.com{link}", callback=lambda r: self.parse_game(r, date))

    def parse_game(self, response, date):
        json_data = response.xpath(".//script[@id='__NEXT_DATA__']/text()").get()
        data = json.loads(json_data)
        game_data_line_history = data["props"]["pageProps"]["lineHistoryModel"]["lineHistory"]
        game_view = game_data_line_history["gameView"]
        odds_views = game_data_line_history["oddsViews"]
        

        away_city = game_view["awayTeam"]["displayName"]
        home_city = game_view["homeTeam"]["displayName"]
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
            return

        base_game = {"GAME_DATE_EST": date, "GAME_ID": matching_games["GAME_ID"].values[0]}
        games = []
        for odds in odds_views:
            sportsbook = odds["sportsbook"]
            odds_history = odds[self._odds_key()]
            if sportsbook not in self.sportsbooks or not odds_history:
                continue
            rows = [
                {**base_game, "AWAY_ODDS": odds["awayOdds"], "HOME_ODDS": odds["homeOdds"], "SPORTSBOOK": sportsbook, "LINE_DATETIME": datetime.strptime(odds["oddsDate"], "%Y-%m-%dT%H:%M:%S%z")}
                for odds in odds_history
            ]
            # closing_odds = odds_history[-1]
            # row_df = {**base_game, "AWAY_ODDS": closing_odds["awayOdds"], "HOME_ODDS": closing_odds["homeOdds"], "SPORTSBOOK": sportsbook}
            games.extend(rows)
                    
        return games

    def translate_city(self, city):
        if city.startswith("L.A."):
            nickname = city.split(" ")[1]
            team = self.teams[self.teams["NICKNAME"] == nickname]
            return team["TEAM_ID"].values[0]
        else:
            team = self.teams[self.teams["CITY"] == city]
            return team["TEAM_ID"].values[0]
    
    def _odds_key(self):
        raise NotImplementedError()

    def _odds_df(self):
        raise NotImplementedError()

    def _odds_url(self, game_date):
        raise NotImplementedError()
