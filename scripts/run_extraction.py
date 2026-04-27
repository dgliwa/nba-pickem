#!/usr/bin/env python3
"""NBA Pick'em - Data Extraction Script

Runs Scrapy spiders to collect:
- Team data 
- Game results from Basketball-Reference (league-wide schedule pages)

Usage:
    python scripts/run_extraction.py --help
    python scripts/run_extraction.py --bball-ref-teams    # Teams with mapping
    python scripts/run_extraction.py --bball-ref-games     # Games (5 seasons, 5 HTTP requests)
"""
import argparse
from twisted.internet import defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from scraping.spiders import (
    BasketballRefTeamsSpider,
    BasketballRefGamesSpider,
)
from crochet import setup, wait_for
import sys


@defer.inlineCallbacks
def _yield_spiders(process, options):
    print(f"Running spiders with options: bball_ref_teams={options.bball_ref_teams}, bball_ref_games={options.bball_ref_games}")
    
    if options.bball_ref_teams:
        print("Starting Basketball-Reference teams spider...")
        yield process.crawl(BasketballRefTeamsSpider)
    
    if options.bball_ref_games:
        print("Starting Basketball-Reference games spider (league-wide)...")
        yield process.crawl(BasketballRefGamesSpider)
    
    if not any([options.bball_ref_teams, options.bball_ref_games]):
        print("Running default: Basketball-Reference games spider...")
        yield process.crawl(BasketballRefGamesSpider)
        yield process.crawl(BasketballRefTeamsSpider)
        yield process.crawl(BasketballRefGamesSpider)


@wait_for(timeout=600)
def __run_spiders(options):
    settings = get_project_settings()
    settings['ITEM_PIPELINES'] = {'scraping.pipelines.BasketballRefPipeline': 300}
    settings['LOG_LEVEL'] = 'DEBUG'
    settings['HTTPERROR_ALLOW_ALL'] = True
    settings['AUTOTHROTTLE_ENABLED'] = False
    process = CrawlerRunner(settings)
    return _yield_spiders(process, options)


def main():
    parser = argparse.ArgumentParser(description="Run NBA Pick'em data extraction from Basketball-Reference")
    parser.add_argument("--bball-ref-teams", action="store_true", help="Scrape team data from Basketball-Reference")
    parser.add_argument("--bball-ref-games", action="store_true", help="Scrape game results from Basketball-Reference (5 seasons)")
    args = parser.parse_args()

    print("Starting extraction...")
    setup()
    __run_spiders(args)
    print("Extraction complete!")


if __name__ == "__main__":
    main()