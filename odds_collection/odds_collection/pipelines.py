# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

import pandas as pd

from odds_collection.spiders.sports_book_moneyline import SportsBookMoneylineSpider
from odds_collection.spiders.sports_book_over_under import SportsBookOverUnderSpider
from odds_collection.spiders.sports_book_spread import SportsBookSpreadSpider


class OddsCollectionPipeline:
    def __init__(self):
        self.games = []


    def process_item(self, item, spider):
        self.games.append(item)
        return item

    def close_spider(self, spider):
        df = pd.DataFrame(self.games)
        if isinstance(spider, SportsBookMoneylineSpider):
            df.to_csv("../data/odds_raw/moneyline.csv", index=False)
        elif isinstance(spider, SportsBookSpreadSpider):
            df.to_csv("../data/odds_raw/spreads.csv", index=False)
        elif isinstance(spider, SportsBookOverUnderSpider):
            df.to_csv("../data/odds_raw/over_under.csv", index=False)
