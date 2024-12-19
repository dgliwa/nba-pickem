from twisted.internet import defer,  asyncioreactor
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from odds_collection.spiders import NbaSeasonMatchupsSpider, NbaGamesSpider
from crochet import setup, wait_for

asyncioreactor.install()


@defer.inlineCallbacks
def yield_spiders(process, reactor) -> None:
  yield process.crawl(NbaSeasonMatchupsSpider)
  yield process.crawl(NbaGamesSpider)
  reactor.stop()

@wait_for(timeout=None)
def run_spiders():
  settings = get_project_settings()
  process = CrawlerRunner(settings)

  from twisted.internet import reactor
  d = yield_spiders(process, reactor)
  return d

def collect_game_data() -> None:
  setup()
  print("running spiders")
  run_spiders()
