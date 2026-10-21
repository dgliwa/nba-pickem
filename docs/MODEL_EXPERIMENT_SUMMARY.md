# NBA Pick'em Model Summary

Single source of truth for the model: data flow, features, evaluation method, results, roadmap.
Reproduce with `uv run python scripts/experiment_models.py --train-start 2016` (selection) and `nba-pickem-train` (final model).

## Data flow

```
basketball-reference schedule pages (played AND upcoming games)
  └─ nba-pickem-daily  (or nba-pickem-load-bball-ref --season N)
       ├─ games table: unplayed games stored with NULL outcome; results filled in as they post;
       │   unplayed games that leave the schedule are dropped (season_sync.py)
       ├─ rolling features recomputed for newly played games (dataloader.py, played games only)
       ├─ pre-game Elo recomputed for every stored game, played and upcoming (update_elo)
       └─ nba-pickem-predict -> game_predictions for today's unplayed games
nba-pickem-train -> worker/best_model.pkl (played games only)
```

Run `nba-pickem-daily` once a day (after results post); it syncs the current season and predicts today.
Game ids are deterministic (`{home}{away}{season}{YYYYMMDD}`), so predictions join to outcomes.
A regular season counts as complete once its playoffs have started, so shortened seasons (2020 bubble, 2021's 72 games) need no special case.
Stored games are regular season only, 2015 onward: playoff games (on/after the playoff start date) and play-in games
(bball-ref's "Play-In Game" remark) are skipped. 2024+ seasons include the NBA Cup final, which doesn't count in the standings.
Backfill with `nba-pickem-extract --since 2015`.

Elo (`compute_elo` in `features.py`) walks all seasons in date order with FiveThirtyEight's NBA parameters: K=20,
margin-of-victory multiplier `(|margin|+3)^0.8 / (7.5 + 0.006·winner_elo_edge)`, 100-point home advantage (none for the
2020 bubble restart), every team starting at 1500 in 2015 and keeping 75% of its distance from 1500 between seasons.
2015 serves as warm-up, so training starts in 2016. Parameters are untuned.

Rolling features use only earlier games in the same season, over a team's last N games at any venue
(`features.py` reproduces these definitions at prediction time; `tests/test_features.py` checks they agree).
bball-ref rate-limits to ~10 requests/minute.

## Evaluation method

The previous summary (April 2026) is superseded. It chose configs on a random 20% split of 2022–2025
(adjacent games leak through rolling features) and picked the winner by its 2026 score, so 2026 was not a clean test.

Now:
- **Selection:** walk-forward folds only: test 2024 and test 2025, each trained on every season from `--train-start` up to the one before. 2,462 test games, standard error ≈ ±1.0 pt.
- **Early season:** `acc_early` scores just the first 14 days of each test season, where same-season rolling stats have no history.
- **Final check:** 2026 (1,231 games, SE ≈ ±1.35 pts) is looked at once, for the selected config and fixed references. Not used to choose.
- Baseline: always pick home = 54.4% (2024–25), 55.5% (2026).

## Results with Elo (October 2026, walk-forward, mean of 2024 and 2025)

Play-in games removed, so the numbers differ slightly from the table further down.

| Feature set | Model | Train from 2022 | Train from 2016 | First 14 days (2016 start) |
|-------------|-------|-----------------|-----------------|----------------------------|
| elo_only (1) | lr | 65.6% | 65.8% | 63.0% |
| elo_plus_home_away (3) | lr | 65.6% | 65.8% | 61.6% |
| diffs_plus_home_away_elo (7) | lr | 65.8% | 65.7% | 62.6% |
| all_features (21, no Elo) | lr | 64.0% | 64.5% | 55.9% |
| diffs_plus_home_away (6, previous selection) | lr | 63.8% | 63.8% | 54.5% |

- Elo adds ≈2 pts overall and ≈8 pts in the first two weeks (rolling stats fall back to defaults until teams have played).
- Rolling stats add nothing on top of Elo; adding them is within noise.
- Training from 2016 instead of 2022 doesn't change accuracy. 2015–2021 still matter as Elo warm-up.
- 2026 single look (trained on 2016–25): elo_only + lr **68.9%** (baseline 55.5%); the old ratings_only + rf_shallow scored 65.4% on the same games.

## Results without Elo (April 2026, walk-forward, mean of 2024 and 2025)

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

**`elo_only` + logistic regression** (StandardScaler → LogisticRegression) on one feature, `d_elo = home_elo_pre − away_elo_pre`.
The fitted intercept carries home advantage.

Rule: simplest config within one SE of the best walk-forward mean. It ties the best mean with one feature.

Previous selection (April 2026): `diffs_plus_home_away` + lr, 6 rolling-stat features (`ROLLING_FEATURES` in `features.py`), 65.9% on 2026.
It predicted 53.8% home for every opening-night game, because no team had same-season history yet.

Canonical artifact: `worker/best_model.pkl` (dict with `model`, `feature_cols`, `model_type`, `feature_set`, `train_seasons`),
written by `nba-pickem-train` on 2016–2026. The older `worker/nba_model*.pkl` files are unused.

## Fixed in this pass

`nba-pickem-predict` was broken and could not have reproduced these numbers:
- Home and away features were merged from dicts with identical keys, so the away team's values overwrote the home team's.
- Prediction used last-N *home-only* games; training used last-N games at any venue.
- `best_model.pkl` held a 15-feature model while prediction supplied 14; scoreboard numeric team ids don't match the DB's abbreviations.
- `game_predictions` had INTEGER team ids and stale columns; it is now `(game_id, home_team_id, away_team_id, game_date_est, predicted_home_team_wins, home_win_probability)`.

NBA's own endpoints (stats.nba.com, cdn.nba.com) are blocked by Akamai from this network, so the schedule comes from bball-ref like everything else.

## Roadmap

Realistic target: a point or two over ~66% walk-forward, not 70%+ (closing betting lines are themselves in the high 60s).
Better benchmark once odds are loaded: accuracy and log-loss vs. implied closing-line probabilities.

| Idea | Impact | Effort |
|------|--------|--------|
| Injury / starting-lineup data (biggest missing signal) | High | Medium–High |
| Odds as a feature / CLV benchmark (SBR scraper exists, untested) | High | Medium |
| Tune Elo (K, home advantage, carryover) on pre-2024 seasons; check calibration | Low–Medium | Low |
| Per-possession ratings (pace, eFG%, TOV) from box scores | Medium | High |
| Additional windows (3/7/20), B2B flag | Low (rest_days showed none) | Low |

Open questions: manual vs. scraped injuries; accuracy-first or CLV-first.
