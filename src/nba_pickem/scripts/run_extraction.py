#!/usr/bin/env python3
"""NBA Pick'em - Data Extraction Script

Placeholder for future custom scraping implementation.

Currently uses the separate Scrapy project at root:
    cd scraping && scrapy crawl ...

Usage:
    nba-pickem-extract --teams     # Extract teams (placeholder)
    nba-pickem-extract --games   # Extract games (placeholder)
"""
import argparse


def main():
    parser = argparse.ArgumentParser(description="Extract NBA Pick'em data")
    parser.add_argument("--teams", action="store_true", help="Extract team data")
    parser.add_argument("--games", action="store_true", help="Extract game data")
    args = parser.parse_args()

    print("Data extraction via Scrapy is currently located at the root 'scraping/' directory.")
    print("To run:")
    print("  cd scraping && scrapy crawl BasketballRefTeamsSpider")
    print("  cd scraping && scrapy crawl BasketballRefGamesSpider")
    print()
    print("Custom extraction (non-Scrapy) coming soon.")


if __name__ == "__main__":
    main()