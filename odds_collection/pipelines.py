# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import pandas as pd

from odds_collection.spiders import NbaGamesSpider
from odds_collection.spiders import NbaSeasonMatchupsSpider
from odds_collection.spiders import NbaTeamsSpider
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
            df.drop_duplicates(inplace=True, subset=["GAME_ID"])
            if not os.path.exists("data/raw/nba_season_matchups.csv"):
                df.to_csv("data/raw/nba_season_matchups.csv", index=False)
            else:
                df.to_csv("data/raw/nba_season_matchups.csv", index=False, mode="a", header=False)
        elif isinstance(spider, NbaGamesSpider):
            if not os.path.exists("data/raw/nba_games.csv"):
                df.to_csv("data/raw/nba_games.csv", index=False)
            else:
                df.to_csv("data/raw/nba_games.csv", index=False, mode="a", header=False)
        elif isinstance(spider, NbaTeamsSpider):
            df.to_csv("data/raw/nba_teams.csv", index=False)
