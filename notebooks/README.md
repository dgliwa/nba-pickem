# Notebooks Module

Jupyter notebooks for model development and analysis.

## Pipeline

The notebooks should be run in order:

1. **00_init.ipynb** - Initial data setup (run scrapers)
2. **01_initial_analysis.ipynb** - Explore data, understand features
3. **02_first_model.ipynb** - Train baseline RandomForest model
4. **03_improve_model.ipynb** - Feature engineering, model tuning
5. **04_combine_odds_data.ipynb** - Add betting odds features
6. **05_examine_weighted_betting.ipynb** - Analyze betting strategy
7. **06_generate_picks_for_day.ipynb** - Generate predictions

## Running Notebooks

```bash
make jupyter
# or
uv run jupyter notebook
```

## Notes

- Notebooks read from CSV files in `data/raw/`
- To use DuckDB instead, update to import from `dataloader.py`
- Trained model saved to `worker/nba_model.pkl`

## Features Used

Current model uses these features:
- `home_team_id`, `away_team_id` - Team identifiers
- `home_win_pct`, `away_win_pct` - Overall win percentage
- `home_home_win_pct`, `away_away_win_pct` - Home/away records
- `home_team_b2b`, `away_team_b2b` - Back-to-back game indicator
- `home_last_10_win_pct`, `away_last_10_win_pct` - Recent form
