# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import pandas as pd

from odds_collection.spiders import NbaGamesSpider
from odds_collection.spiders import NbaSeasonMatchupsSpider
from odds_collection.spiders import SportsBookMoneylineSpider
from odds_collection.spiders import SportsBookOverUnderSpider
from odds_collection.spiders import SportsBookSpreadSpider


class OddsCollectionPipeline:
    def __init__(self):
        self.games = []


    def process_item(self, item, spider):
        self.games.append(item)
        return item

    def close_spider(self, spider):
        df = pd.DataFrame(self.games)
        if isinstance(spider, SportsBookMoneylineSpider):
            df.to_csv("data/odds_raw/moneyline.csv", index=False)
        elif isinstance(spider, SportsBookSpreadSpider):
            df.to_csv("data/odds_raw/spreads.csv", index=False)
        elif isinstance(spider, SportsBookOverUnderSpider):
            df.to_csv("data/odds_raw/over_under.csv", index=False)
        elif isinstance(spider, NbaSeasonMatchupsSpider):
            df.drop_duplicates(inplace=True, subset=["GAME_ID"])
            df.to_csv("data/nba_season_matchups.csv", index=False)
        elif isinstance(spider, NbaGamesSpider):
            if not os.path.exists("data/nba_games.csv"):
                df.to_csv("data/nba_games.csv", index=False)
            else:
                df.to_csv("data/nba_games.csv", index=False, mode="a", header=False)
