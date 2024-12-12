# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import pandas as pd

from scraping.spiders import NbaGamesSpider
from scraping.spiders import NbaSeasonMatchupsSpider
from scraping.spiders import NbaTeamsSpider
from scraping.spiders import SportsBookMoneylineSpider
from scraping.spiders import SportsBookOverUnderSpider
from scraping.spiders import SportsBookSpreadSpider
from scraping.data import save_games_df, save_teams_df, save_matchups_df


class OddsCollectionPipeline:
    def __init__(self):
        self.games = []


    def process_item(self, item, spider):
        self.games.append(item)
        return item

    def close_spider(self, spider):
        spider.logger.info("Closing spider")
        spider.logger.info(f"Saving {len(self.games)} games")
        if not self.games:
            return
        df = pd.DataFrame(self.games)
        if isinstance(spider, SportsBookMoneylineSpider):
            if not os.path.exists("data/raw/odds/moneyline.csv"):
                df.to_csv("data/raw/odds/moneyline.csv", index=False)
            else:
                df.to_csv("data/raw/odds/moneyline.csv", index=False, mode="a", header=False)
        elif isinstance(spider, SportsBookSpreadSpider):
            if not os.path.exists("data/raw/odds/spreads.csv"):
                df.to_csv("data/raw/odds/spread.csv", index=False)
            else:
                df.to_csv("data/raw/odds/spread.csv", index=False, mode="a", header=False)
        elif isinstance(spider, SportsBookOverUnderSpider):
            if not os.path.exists("data/raw/odds/over_under.csv"):
                df.to_csv("data/raw/odds/over_under.csv", index=False)
            else:
                df.to_csv("data/raw/odds/over_under.csv", index=False, mode="a", header=False)
        elif isinstance(spider, NbaSeasonMatchupsSpider):
            spider.logger.info("Saving matchups")
            save_matchups_df(df)
        elif isinstance(spider, NbaGamesSpider):
            save_games_df(df)
        elif isinstance(spider, NbaTeamsSpider):
            save_teams_df(df)
