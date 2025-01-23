from dao import retrieve_moneylines_df
from scraping.spiders.base_sports_book_scraper import BaseSportsBookScraper


class SportsBookMoneylineSpider(BaseSportsBookScraper):
    name = "sports_book_moneyline"

    def _odds_df(self):
        return retrieve_moneylines_df()

    def _odds_url(self, game_date):
        return f"https://www.sportsbookreview.com/betting-odds/nba-basketball/money-line/full-game/?date={game_date.strftime('%Y-%m-%d')}"

    def _odds_key(self):
        return "moneyLineHistory"
