import scrapy
import os
import pandas as pd

SPORTSBOOKS = [
    "fanduel",
    "mgm",
    "draftkings",
    "caesars"
]


class SportsBookSpreadSpider(scrapy.Spider):
    download_delay = 0.25
    name = "sports_book_spread"
    allowed_domains = ["sportsbookreview.com"]
    start_urls = ["https://sportsbookreview.com"]

    def __init__(self):
        if os.path.exists("data/raw/nba_games.csv"):
            self.nba_games = pd.read_csv("data/raw/nba_games.csv", dtype={"GAME_ID": str}).sort_values("GAME_DATE_EST")

        if os.path.exists("data/raw/odds/spread.csv"):
            self.spread = pd.read_csv("data/raw/odds/spread.csv", dtype={"GAME_ID": str}).sort_values("date")
        else:
            self.spread = pd.DataFrame()

    def start_requests(self):
        self.nba_games = self.nba_games[self.nba_games["SEASON"] >= 2019]
        if len(self.spread) > 0:
            self.nba_games = self.nba_games[~self.nba_games["GAME_DATE_EST"].isin(self.spread["date"].unique())]
        game_dates = self.nba_games["GAME_DATE_EST"].unique()
        for game_date in game_dates:
            url = f"https://www.sportsbookreview.com/betting-odds/nba-basketball/?date={game_date}"
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        date = response.url.split("=")[-1]
        odds_rows = response.css("#tbody-nba > div.flex-row")

        games = []
        for row in odds_rows:
            participants = row.xpath(".//span[re:test(@class, 'participant')]/text()")
            row_df = {"date": date}

            away, home = [p.get().strip() for p in participants]
            row_df.update({"away": away, "home": home})
            for sportsbook in SPORTSBOOKS:
                away_spread, away_odds, home_spread, home_odds = self.parse_odds(sportsbook, row)
                row_df.update({f"{sportsbook}_away_spread": away_spread, f"{sportsbook}_away_odds": away_odds, f"{sportsbook}_home_spread": home_spread, f"{sportsbook}_home_odds": home_odds})
            games.append(row_df)
        return games



    def parse_odds(self, sportsbook, odds_row):
        odds = odds_row.xpath(f".//a[re:test(@href, '{sportsbook}')]/div/div/span[@role='button']/span/text()")
        self.log(f"Odds: {odds}")
        if not odds:
            return (pd.NA, pd.NA, pd.NA, pd.NA)
        away_spread = float(odds[0].get()) if odds[0].get() != "PK" else 0.0
        home_spread = float(odds[2].get()) if odds[2].get() != "PK" else 0.0
        return (away_spread, int(odds[1].get()), home_spread, int(odds[3].get()))
