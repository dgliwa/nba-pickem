# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

from odds_collection.spiders.nba_season_matchups import NbaSeasonMatchupsSpider
from odds_collection.spiders.sports_book_moneyline import SportsBookMoneylineSpider
from odds_collection.spiders.sports_book_spread import SportsBookSpreadSpider
from odds_collection.spiders.sports_book_over_under import SportsBookOverUnderSpider

__all__ = ["NbaSeasonMatchupsSpider","SportsBookMoneylineSpider", "SportsBookSpreadSpider", "SportsBookOverUnderSpider"]
