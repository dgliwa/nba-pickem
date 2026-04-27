# NBA Pick'em Model Improvement Plan

## Architecture Overview

### Data Flow

```
bball-ref.com (schedule pages)
    └──> nba-pickem-load-bball-ref --all-seasons
              └──> games table (with base data)
                    └──> feature computation (as-of rolling stats)
                          └──> trained model (pickle)
                                └──> predictions
```

### How Teams Are Fetched

**Source**: `basketball-reference.com`

**Script**: `src/nba_pickem/scripts/load_bball_ref_data.py`

**Process**:
1. `nba-pickem-load-bball-ref --teams` loads team aliases and team records
2. Team aliases table: maps legacy abbreviations (BRK→BKN, CHO→CHA, PHO→PHX)
3. Teams stored with VARCHAR abbreviations (GSW, BKN, etc.) not NBA API integer IDs

### How Games Are Populated for Each Season

**Source**: `https://www.basketball-reference.com/leagues/NBA_{season}_games.html`

**Process**:
1. Fetch monthly pages (october through june) to get all games in season
2. Parse HTML schedule tables for:
   - `game_id`: `{home}{away}{season}{date}` (e.g., "GSWLAL202520241022")
   - `home_team_id`: Home team abbreviation (VARCHAR)
   - `away_team_id`: Away team abbreviation (VARCHAR)
   - `game_date_est`: Game date
   - `season`: Season year (2022-2026)
   - `home_team_points`, `away_team_points`: Score
   - `home_team_wins`: Boolean (derived from score)

**Command**: `nba-pickem-load-bball-ref --season {year} --force`

### Features Calculated

**Computed in**: `_compute_features_internal()` in `dataloader.py`

**Rolling window features**: Computed "as-of" each game (using only prior games in same season)

| Feature | Description | Lookback |
|---------|-------------|----------|
| `home_win_pct_5` | Home team win % | Last 5 games |
| `home_win_pct_10` | Home team win % | Last 10 games |
| `away_win_pct_5` | Away team win % | Last 5 games |
| `away_win_pct_10` | Away team win % | Last 10 games |
| `off_rtg_5` | Home team offensive rating (avg pts scored) | Last 5 games |
| `off_rtg_10` | Home team offensive rating | Last 10 games |
| `def_rtg_5` | Home team defensive rating (avg pts allowed) | Last 5 games |
| `def_rtg_10` | Home team defensive rating | Last 10 games |
| `off_rtg_5` (away) | Away team offensive rating | Last 5 games |
| `off_rtg_10` (away) | Away team offensive rating | Last 10 games |
| `def_rtg_5` (away) | Away team defensive rating | Last 5 games |
| `def_rtg_10` (away) | Away team defensive rating | Last 10 games |
| `margin_5` | Home team point differential | Last 5 games |
| `margin_10` | Home team point differential | Last 10 games |
| `rest_days` | Days since last game (max of both teams) | N/A |
| `home_wpct_home` | Home team win % in home games | Last 10 home games |
| `away_wpct_away` | Away team win % in away games | Last 10 away games |

**Total features**: 16 rolling features + 2 team encodings = 18 features

---

## Models

### Model Types

| Model | Type | Output | Saved As |
|-------|------|--------|----------|
| Classifier | RandomForest (binary) | home wins: yes/no | `nba_model_classifier.pkl` |
| Regressor | RandomForest (regression) | point margin (home - away) | `nba_model_regressor.pkl` |

### Shared Configuration

```python
RandomForestClassifier/Regressor(
    max_depth=7,
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)
```

### Performance Comparison

| Model | Train Accuracy | Test Accuracy (20% holdout) | 2026 Holdout |
|-------|----------------|---------------------------|-------------|
| Classifier | 73.4% | 62.1% | **63.5%** |
| Regressor | MAE: 10.09 | MAE: 11.02 | **63.8%** |

**Winner**: Regressor (63.8% vs 63.5%)

### Current Problem with Model

1. **Target (70%) not met**: Current accuracy is ~64% vs target 70%
2. **Limited features**: No player-level data, no injury information, no ELO ratings
3. **No odds integration**: CLV-based betting model not implemented
4. **Data source limitations**: bball-ref rate-limits to 10 requests/minute

---

## Gap Analysis

### What's Missing for Better Accuracy

| Gap | Impact | Difficulty |
|-----|--------|------------|
| Player-based ELO (starting 5) | HIGH | Medium |
| Injury status tracking | HIGH | Low |
| Home/away splits more granular | MEDIUM | Low |
| Opponent-adjusted metrics | MEDIUM | Medium |
| Advanced metrics (pace, TOV, eFG%) | MEDIUM | High |
| Odds/CLV integration | HIGH | Medium |
| More training data (older seasons) | MEDIUM | Low |
| Model tuning (XGBoost, more trees) | LOW | Low |

---

## Upcoming Proposed Changes

### Priority 1: Quick Wins (Low Effort, Some Impact)

#### 1.1 Hyperparameter Tuning
- **Change**: Increase `n_estimators`, tune `max_depth`
- **Data needed**: Current games table
- **Expected improvement**: 1-3%
- **Priority**: LOW

#### 1.2 Add More Training Seasons
- **Change**: Backfill 2015-2021 seasons (if data available from bball-ref)
- **Data source**: bball-ref historical schedules
- **Expected improvement**: 2-4% (more training data)
- **Priority**: MEDIUM

### Priority 2: Feature Engineering (Medium Effort, High Impact)

#### 2.1 Granular Home/Away Splits
- **Change**: Calculate separate win% for home games only / away games only per team
- **Data needed**: Already in games table, just need new computation
- **Expected improvement**: 1-2%
- **Priority**: MEDIUM

#### 2.2 Rest & Travel Features
- **Change**: Add back-to-back indicator, days off, travel distance (rough approximation)
- **Data needed**: Already calculable from schedule
- **Expected improvement**: 1-2%
- **Priority**: MEDIUM

### Priority 3: Player-Based Features (High Effort, High Impact)

#### 3.1 Starting 5 Production Proxy
- **Change**: Scrape box scores, compute average player "contribution" for each team
- **Data source**: Need to scrape bball-ref box scores per game (10+ requests/minute)
- **Expected improvement**: 3-5%
- **Priority**: HIGH
- **Risk**: Rate limiting complexity

#### 3.2 Injury Status Tracking
- **Change**: Manual or scraped injury list
- **Data source**: Manual input or injury report scraper
- **Expected improvement**: 2-4%
- **Priority**: MEDIUM

### Priority 4: CLV Betting Integration (Future Phase)

#### 4.1 Odds Infrastructure
- **Change**: Integrate sportsbook odds, track opening/closing lines
- **Data source**: SBR scraper (exists but untested)
- **Expected improvement**: Enables CLV tracking
- **Priority**: LOW (for prediction accuracy)

---

## Implementation Recommendation

### Immediate Next Steps

1. **Tune hyperparameters** on regressor model (quick win)
2. **Compute additional home/away features** (feature engineering)
3. **Backtest on historical data** to validate improvements

### Longer Term

1. Add player-based features if time/resources allow
2. Integrate odds for CLV tracking

---

## Files Reference

| File | Purpose |
|------|---------|
| `src/nba_pickem/dataloader.py` | Data loading, feature computation |
| `src/nba_pickem/scripts/load_bball_ref_data.py` | bball-ref data extraction |
| `src/nba_pickem/scripts/train_model.py` | Model training |
| `src/nba_pickem/scripts/run_prediction.py` | Prediction generation |
| `data/nba_pickem.duckdb` | DuckDB database |
| `worker/nba_model.pkl` | Best performing model (regressor) |

---

## Questions for User

1. Should we prioritize accuracy improvement (more features) or betting/CLV integration first?
2. Do you want to manually track injuries, or should I try to find a data source?
3. Is backfilling older seasons a priority, or focus on improving current model first?