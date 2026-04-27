# Scripts Module

CLI entry points for the NBA Pick'em pipeline.

## Scripts

| Script | Purpose |
|--------|---------|
| `setup.py` | Initialize DuckDB, optionally load seed data |
| `run_extraction.py` | Run Scrapy spiders to collect data |
| `run_prediction.py` | Generate predictions for a date |

## Usage

```bash
# Initialize database
python scripts/setup.py

# Initialize with seed data
python scripts/setup.py --load

# Extract data
python scripts/run_extraction.py
python scripts/run_extraction.py --teams    # Teams only
python scripts/run_extraction.py --games    # Games only
python scripts/run_extraction.py --odds     # Odds only

# Generate predictions
python scripts/run_prediction.py                    # Today's games
python scripts/run_prediction.py 2025-04-20         # Specific date
```

## Makefile Targets

These scripts are also accessible via `make`:
```bash
make init      # Initialize DB
make extract   # Run extraction
make predict   # Generate predictions
```
