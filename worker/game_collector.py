from celery import shared_task
from twisted.internet import defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from scraping.spiders import NbaSeasonMatchupsSpider, NbaGamesSpider
from crochet import setup, wait_for
from worker.game_predictor import predict_todays_games



@defer.inlineCallbacks
def yield_spiders(process) -> None:
  yield process.crawl(NbaSeasonMatchupsSpider)
  yield process.crawl(NbaGamesSpider)

@wait_for(timeout=None)
def run_spiders():
  settings = get_project_settings()
  process = CrawlerRunner(settings)

  d = yield_spiders(process)
  return d

@shared_task(ignore_result=True)
def collect_game_data() -> None:
  setup()
  run_spiders()
  predict_todays_games.delay()
