# NBA Pick'em

NBA game prediction system using machine learning to predict game winners.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  EXTRACTION PIPELINE                                   │
│  Scripts or Scrapy collect:                           │
│  - Team data                                      │
│  - Game results                                  │
│  - Matchup schedule                               │
│  - Betting odds                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STORAGE                                              │
│  DuckDB (data/nba_pickem.duckdb)                       │
│  Tables: teams, games, game_predictions, moneyline_odds  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  MODELING PIPELINE                                     │
│  Jupyter notebooks for:                               │
│  - Data exploration                                 │
│  - Feature engineering                             │
│  - Model training                                 │
│  - Evaluation                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PREDICTION PIPELINE                                   │
│  Run predictions for any date:                      │
│  nba-pickem-predict 2025-04-20                    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install package in editable mode
make install

# Initialize database
make init

# Or with seed data from CSV
make init-load

# Generate predictions
make predict
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `nba-pickem` | Show version and available commands |
| `nba-pickem-init` | Initialize empty DuckDB |
| `nba-pickem-init --load` | Initialize with seed data from CSV |
| `nba-pickem-extract` | Extract data (placeholder) |
| `nba-pickem-predict` | Generate predictions for today |
| `nba-pickem-predict 2025-04-20` | Predict specific date |
| `nba-pickem-train` | Train prediction model |
| `nba-pickem-openclaw daily` | Refresh data, generate picks, and emit the automation report as JSON |
| `nba-pickem-openclaw report` | Read the saved automation report as JSON |
| `python -m nba_pickem` | Run as module |

Or use `make` targets:

```bash
make install    # Install dependencies
make init      # Initialize empty DB
make predict   # Generate predictions
make jupyter  # Start Jupyter server
make clean    # Remove DB and cache files
```

## Project Structure

```
nba-pickem/
├── src/nba_pickem/         # Python package
│   ├── __init__.py       # Exports
│   ├── __main__.py       # python -m entry
│   ├── config.py       # Paths (PACKAGE_ROOT, DATA_DIR, DB_PATH)
│   ├── dataloader.py   # DuckDB data layer
│   └── scripts/       # CLI scripts
│       ├── setup.py
│       ├── run_extraction.py
│       ├── run_prediction.py
│       └── train_model.py
├── scraping/           # Scrapy spiders (separate project)
├── data/             # Data files (duckdb, models, CSVs)
│   └── raw/         # Raw seed data
├── worker/           # Trained model
│   └── nba_model.pkl
├── notebooks/        # Model training pipeline
└── Makefile
```

## Requirements

- Python 3.11 - 3.13 (not 3.14 yet due to PyO3 compatibility)
- [uv](https://docs.astral.sh/uv/) for package management
- scikit-learn for ML
- DuckDB for storage
- Scrapy for data collection (optional)

## OpenClaw automation

The repository includes an OpenClaw tool plugin with three deterministic tools:

- `nba_pickem_daily_publish` refreshes the current season, saves today's picks, and idempotently sends two separate Discord messages to `#bets`.
- `nba_pickem_report` reads today's picks, previous-day results, current-week accuracy, and current-season accuracy without changing data.
- `nba_pickem_publication_status` reports full or partial Discord delivery for a date.

The daily publisher records each message delivery separately under OpenClaw state, so a retry resumes after a partial failure without duplicating the picks message. Accuracy counts only completed games with saved pregame predictions. The week begins Monday, and all date boundaries use the NBA's US Eastern date.

The JSON bridge can also be run directly:

```bash
nba-pickem-openclaw report --date 2026-10-21
nba-pickem-openclaw daily
```

The configured OpenClaw scheduler runs the publisher every morning. See [`docs/DISCORD_DISPLAY_OPTIONS.md`](docs/DISCORD_DISPLAY_OPTIONS.md) for richer Discord display options.

## Cron Usage

For installations without OpenClaw:

```cron
# Daily prediction at 8am
0 8 * * * cd /path/to/nba-pickem && nba-pickem-extract && nba-pickem-predict
```

## License

MIT