import scrapy

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

    def start_requests(self):
        df = pd.read_csv("../data/games.csv")
        df = df.sort_values(by="GAME_DATE_EST", ascending=False)
        df = df[df["SEASON"] >= 2019]
        game_dates = df["GAME_DATE_EST"].unique()
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
