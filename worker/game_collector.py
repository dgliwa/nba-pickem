from celery import shared_task
from twisted.internet import defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from scraping.spiders import NbaSeasonMatchupsSpider, NbaGamesSpider
from crochet import setup, wait_for
import numpy as np
from worker.game_predictor import predict_todays_games
from dao import retrieve_game_predictions_df
from zoneinfo import ZoneInfo
from datetime import datetime


@defer.inlineCallbacks
def _yield_spiders(process) -> None:
    yield process.crawl(NbaSeasonMatchupsSpider)
    yield process.crawl(NbaGamesSpider)


@wait_for(timeout=None)
def __run_spiders():
    settings = get_project_settings()
    process = CrawlerRunner(settings)

    d = _yield_spiders(process)
    return d


@shared_task(ignore_result=True)
def collect_game_data() -> None:
    game_date = datetime.now(ZoneInfo('US/Eastern')).date()
    existing_predictions = retrieve_game_predictions_df(game_date)
    if not existing_predictions[existing_predictions["GAME_DATE_EST"] == np.datetime64(game_date)].empty:
        return
    setup()
    __run_spiders()
    predict_todays_games.delay(game_date)
