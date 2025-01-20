import logging
import scrapy
import pandas as pd
from dao import retrieve_moneylines_df, retrieve_games_df, retrieve_teams_df
from scraping.spiders.base_sports_book_scraper import BaseSportsBookScraper

SPORTSBOOKS = [
    "fanduel",
    "mgm",
    "draftkings",
    "caesars",
    "rivers"
]


class SportsBookMoneylineSpider(BaseSportsBookScraper):
    name = "sports_book_moneyline"

    def _odds_df(self):
        return retrieve_moneylines_df()

    def _odds_url(self, game_date):
        return f"https://www.sportsbookreview.com/betting-odds/nba-basketball/money-line/full-game/?date={game_date.strftime('%Y-%m-%d')}"
