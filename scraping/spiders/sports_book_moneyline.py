import scrapy
import os
import pandas as pd

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
        if os.path.exists("data/raw/nba_games.csv"):
            self.nba_games = pd.read_csv("data/raw/nba_games.csv", dtype={"GAME_ID": str}).sort_values("GAME_DATE_EST")

        if os.path.exists("data/raw/odds/moneyline.csv"):
            self.moneylines = pd.read_csv("data/raw/odds/moneyline.csv", dtype={"GAME_ID": str}).sort_values("date")
        else:
            self.moneylines = pd.DataFrame()
        super().__init__()


    def start_requests(self):
        self.nba_games = self.nba_games[self.nba_games["SEASON"] >= 2019]
        if len(self.moneylines) > 0:
            self.nba_games = self.nba_games[~self.nba_games["GAME_DATE_EST"].isin(self.moneylines["date"].unique())]

        game_dates = self.nba_games["GAME_DATE_EST"].unique()
        for game_date in game_dates:
            url = f"https://www.sportsbookreview.com/betting-odds/nba-basketball/money-line/full-game/?date={game_date}"
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
                away_odds, home_odds = self.parse_odds(sportsbook, row)
                row_df.update({f"{sportsbook}_away_odds": away_odds, f"{sportsbook}_home_odds": home_odds})
            games.append(row_df)
        return games



    def parse_odds(self, sportsbook, odds_row):
        odds = odds_row.xpath(f".//a[re:test(@href, '{sportsbook}')]/div/div/span[@role='button']/span[2]/text()")
        self.log(f"Odds: {odds}")
        if not odds:
            return (pd.NA, pd.NA)
        return (int(odds[0].get()), int(odds[1].get()))
