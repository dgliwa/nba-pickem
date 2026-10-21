# NBA Pick'em Model Summary

Single source of truth for the model: data flow, features, evaluation method, results, roadmap.
Reproduce with `uv run python scripts/experiment_models.py` (selection) and `nba-pickem-train` (final model).

## Data flow

```
basketball-reference schedule pages
  └─ nba-pickem-load-bball-ref --season {year}   -> games table (DuckDB, team ids are abbreviations)
       └─ recompute_all_features()               -> as-of rolling features per game (dataloader.py)
            └─ nba-pickem-train                  -> worker/best_model.pkl
                 └─ nba-pickem-predict [date]    -> game_predictions table
```

Rolling features use only earlier games in the same season, over a team's last N games at any venue
(`features.py` reproduces these definitions at prediction time; `tests/test_features.py` checks they agree).
bball-ref rate-limits to ~10 requests/minute.

## Evaluation method

The previous summary (April 2026) is superseded. It chose configs on a random 20% split of 2022–2025
(adjacent games leak through rolling features) and picked the winner by its 2026 score, so 2026 was not a clean test.

Now:
- **Selection:** walk-forward folds only: test 2024 trained on 2022–23, test 2025 trained on 2022–24. 2,474 test games, standard error ≈ ±1.0 pt.
- **Final check:** 2026 (1,237 games, SE ≈ ±1.35 pts) is looked at once, for the selected config and fixed references. Not used to choose.
- Baseline: always pick home = 54.4% (2024–25), 55.5% (2026).

## Results (walk-forward, mean of 2024 and 2025)

| Feature set | Model | 2024 | 2025 | Mean |
|-------------|-------|------|------|------|
| all_features (21) | lr | 64.6% | 63.3% | 63.95% |
| diffs_plus_home_away (6) | rf_shallow | 63.9% | 63.9% | 63.86% |
| diffs_plus_home_away (6) | lr | 64.2% | 63.4% | 63.78% |
| ratings_no_margin (10) | lr | 64.4% | 63.2% | 63.78% |
| ratings_only (14) | lr | 64.3% | 63.2% | 63.74% |
| ratings_only (14) | rf_shallow *(old "winner")* | 63.5% | 61.9% | 62.69% |
| any set | gb | | | 58.6–62.0% |

**Takeaway: the top ~25 configurations are statistically indistinguishable** (spread ≈ 1.5 pts vs SE ≈ 1 pt).
Honest ceiling for rolling team stats is ≈ 64% walk-forward over a 54–55% baseline.

What the ablations do support:
- Gradient boosting is consistently worst (overfits). Deeper RFs don't help.
- `margin_*` features are exactly `off_rtg − def_rtg` (max diff 0.01, rounding). Dropping them leaves LR unchanged (63.78% vs 63.74%).
- Team-id encodings add nothing for LR (and an ordinal code is meaningless there) and aren't needed.
- `rest_days` does not help. Win-pct-only is slightly worse than ratings/margins.
- "Ratings beat win%" from the old summary is not clearly supported; margin and win% differentials together do as well as anything.

## Selected model

**`diffs_plus_home_away` + logistic regression** (StandardScaler → LogisticRegression), 6 features:
`d_margin_5`, `d_margin_10`, `d_win_pct_5`, `d_win_pct_10`, `home_wpct_home`, `away_wpct_away`.

Rule: simplest config within one SE of the best walk-forward mean. It is 0.17 pt behind the top config with 6 features instead of 21,
no team encoding, a 1.7 KB model instead of an 8.5 MB forest, and native probabilities (calibration not yet checked).

2026 single look (trained on 2022–25): **65.9%** (baseline 55.5%). For reference, the old winner scored 66.0% and the walk-forward leader
(all_features + lr) 65.3% on the same games, i.e. all within noise.

Canonical artifact: `worker/best_model.pkl` (dict with `model`, `feature_cols`, `model_type`, `feature_set`, `train_seasons`),
written by `nba-pickem-train` on 2022–2026. The older `worker/nba_model*.pkl` files are unused.

## Fixed in this pass

`nba-pickem-predict` was broken and could not have reproduced these numbers:
- Home and away features were merged from dicts with identical keys, so the away team's values overwrote the home team's.
- Prediction used last-N *home-only* games; training used last-N games at any venue.
- `best_model.pkl` held a 15-feature model while prediction supplied 14; scoreboard numeric team ids don't match the DB's abbreviations.
- `game_predictions` had INTEGER team ids and stale columns; it is now `(game_id, home_team_id, away_team_id, game_date_est, predicted_home_team_wins, home_win_probability)`.

The schedule now comes from ESPN's public scoreboard (`schedule.py`, tested against a saved real response in `tests/fixtures/`); stats.nba.com and cdn.nba.com were unreachable (Akamai blocking).

## Roadmap

Realistic target: a few points of lift over ~64% walk-forward, not 70% (closing betting lines are themselves in the high 60s).
Better benchmark once odds are loaded: accuracy and log-loss vs. implied closing-line probabilities.

| Idea | Impact | Effort |
|------|--------|--------|
| Injury / starting-lineup data (biggest missing signal) | High | Medium–High |
| Odds as a feature / CLV benchmark (SBR scraper exists, untested) | High | Medium |
| Elo or opponent-adjusted ratings | Medium | Medium |
| Backfill 2015–2021 (more training data; check regime change) | Medium | Low |
| Per-possession ratings (pace, eFG%, TOV) from box scores | Medium | High |
| Additional windows (3/7/20), B2B flag | Low (rest_days showed none) | Low |

Open questions: manual vs. scraped injuries; accuracy-first or CLV-first.
