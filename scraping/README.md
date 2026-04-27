# Scraping Module

Data collection using Scrapy spiders.

## Spiders

| Spider | Purpose |
|--------|---------|
| `nba_teams.py` | Collect team IDs, names, abbreviations |
| `nba_games.py` | Collect game scores and stats |
| `nba_season_matchups.py` | Collect season schedule |
| `sports_book_moneyline.py` | Collect moneyline odds |
| `sports_book_spread.py` | Collect point spread odds |
| `sports_book_over_under.py` | Collect over/under totals |

## Running Spiders

```bash
# Run all spiders
python scripts/run_extraction.py

# Run specific spider
uv run scrapy crawl nba_teams
uv run scrapy crawl nba_games
```

## Data Sources

- Game data: [stats.nba.com](https://stats.nba.com/)
- Betting odds: [sportsbookreview](https://www.sportsbookreview.com)

## Configuration

Settings in `scraping/settings.py` control request rates, user agents, etc.

## Output

Spider outputs are stored in:
- CSV files in `data/raw/`
- Loaded into DuckDB via `dataloader.py`
