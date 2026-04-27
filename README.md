# NBA Pick'em

NBA game prediction system using machine learning to predict game winners.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  EXTRACTION PIPELINE                                      │
│  Scrapy spiders collect:                                │
│  - Team data (nba_teams.py)                             │
│  - Game results (nba_games.py)                          │
│  - Matchup schedule (nba_season_matchups.py)              │
│  - Betting odds (sports_book_*.py)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STORAGE                                               │
│  DuckDB (nba_pickem.duckdb)                            │
│  Tables: teams, games, game_predictions, moneyline_odds   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  MODELING PIPELINE                                      │
│  Jupyter notebooks for:                                │
│  - Data exploration                                   │
│  - Feature engineering                                │
│  - Model training                                     │
│  - Evaluation                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PREDICTION PIPELINE                                    │
│  Run predictions for any date:                         │
│  python scripts/run_prediction.py 2025-04-20          │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install dependencies
make install

# Initialize database
make init

# Or with seed data from CSV
python scripts/setup.py --load

# Extract current data
make extract

# Generate predictions
make predict
```

## Available Commands

| Command | Description |
|---------|-------------|
| `make install` | Install dependencies with uv |
| `make init` | Initialize empty DuckDB |
| `make extract` | Run all Scrapy spiders |
| `make extract-teams` | Run only team spider |
| `make extract-games` | Run only games spider |
| `make predict` | Generate predictions for today |
| `make jupyter` | Start Jupyter server |
| `make clean` | Remove DB and cache files |

## Project Structure

```
nba-pickem/
├── scraping/           # Scrapy spiders for data collection
├── scripts/           # CLI entry points
│   ├── setup.py       # Database initialization
│   ├── run_extraction.py
│   └── run_prediction.py
├── notebooks/        # Model training pipeline
├── dataloader.py     # DuckDB data layer
├── services/         # (deprecated - needs removal)
└── worker/
    └── nba_model.pkl # Trained model
```

## Requirements

- Python 3.11 - 3.13 (not 3.14 yet due to PyO3 compatibility)
- [uv](https://docs.astral.sh/uv/) for package management
- Scrapy for data collection
- scikit-learn for ML
- DuckDB for storage

## License

MIT