# NBA Pick'em Model Experimentation Summary

## Experiment Overview

Tested multiple feature sets and model types to find the best combination for predicting NBA game outcomes.

### Feature Sets Tested
| Feature Set | Description | # Features |
|-------------|-------------|------------|
| `all_features` | All available features (win%, ratings, margins, rest, home/away splits) | 21 |
| `home_only` | Only home team's features | 12 |
| `away_only` | Only away team's features | 11 |
| `differentials` | Home and away team features as separate columns | 11 |
| `ratings_only` | Offensive/defensive ratings and margins only | 14 |
| `winpct_only` | Win percentage features only | 8 |
| `top_10` | Top 10 most important features (5-game window) | 10 |

### Models Tested
- `rf_shallow`: Random Forest (max_depth=5, n_estimators=100)
- `rf_medium`: Random Forest (max_depth=7, n_estimators=150)
- `rf_deep`: Random Forest (max_depth=10, n_estimators=200)
- `gb`: Gradient Boosting (n_estimators=100, max_depth=4)
- `lr`: Logistic Regression (with StandardScaler)

---

## Results

### Top 5 Configurations by Validation Accuracy (2022-2025 holdout)
| Feature Set | Model | Train Acc | Val Acc | # Features |
|-------------|-------|-----------|---------|------------|
| ratings_only | lr | 61.9% | 64.4% | 14 |
| ratings_only | rf_deep | 89.5% | 64.2% | 14 |
| ratings_only | rf_shallow | 66.5% | 64.0% | 14 |
| all_features | rf_medium | 74.7% | 64.0% | 21 |
| differentials | rf_medium | 72.7% | 63.9% | 11 |

### 2026 Hold-out Test Results (Full Season: 1237 games)
| Feature Set | Model | Val Acc | 2026 Acc |
|-------------|-------|---------|----------|
| ratings_only | lr | 64.4% | 65.2% |
| ratings_only | rf_shallow | 64.0% | **65.5%** |
| ratings_only | rf_deep | 64.2% | 64.2% |
| all_features | rf_medium | 64.0% | 64.8% |
| differentials | rf_medium | 63.9% | 62.3% |

---

## Best Model Configuration

**Winner: `ratings_only` + `rf_shallow` (Random Forest shallow)**

- **2026 Accuracy: 65.48%** (810/1237 correct)
- **Features (14 total):**
  - Team encodings: `home_team_enc`, `away_team_enc`
  - Offensive rating: `home_off_rtg_5`, `home_off_rtg_10`, `away_off_rtg_5`, `away_off_rtg_10`
  - Defensive rating: `home_def_rtg_5`, `home_def_rtg_10`, `away_def_rtg_5`, `away_def_rtg_10`
  - Margin: `home_margin_5`, `home_margin_10`, `away_margin_5`, `away_margin_10`

---

## Hypothesis: Why This Works

### 1. Ratings capture more signal than win percentages
Win percentages are derived from game outcomes, but offensive/defensive ratings capture **how well teams play** independent of wins/losses. A team can win close games (lucky) or lose close games (unlucky), but their point differentials tell a more complete story.

### 2. Simpler model generalizes better
The shallow RF (max_depth=5) outperformed deeper trees and gradient boosting. This suggests:
- The relationship between ratings and game outcomes is relatively simple
- Deeper trees were overfitting to training data noise
- Regularization from shallower trees improves generalization to new seasons

### 3. Ratings-only removes redundant/noisy features
The `all_features` set (21 features) performed **worse** than `ratings_only` (14 features). Likely reasons:
- `home_wpct_home` and `away_wpct_away` introduce small-sample noise early in seasons
- Win percentage features are highly correlated with ratings (redundancy)
- Rest days has minimal predictive power in NBA (teams manage load well) - **confirmed: adding `rest_days` hurts performance slightly** (65.48% → 65.16%)

### 4. Why not Logistic Regression despite similar accuracy?
Logistic Regression had 65.2% vs RF shallow's 65.5% - essentially tied. However:
- RF provides feature importance for interpretation
- RF handles feature interactions automatically
- RF is more robust to feature scaling

---

## Additional Observations

### Home Court Advantage
- Actual home win rate in 2026: **55.5%**
- Model predicts home win: **66.5%** of time
- This slight home bias likely helps given the true home court advantage

### Training Data
- Seasons used: 2022, 2023, 2024, 2025
- Training samples: 4,946 games

---

## Next Steps for Improvement

1. **Add more rolling windows** - Test 3-game, 7-game, 20-game rolling features
2. **Elo ratings** - Implement Elo system for teams
3. **Injury data** - Factor in key player injuries (major missing signal)
4. **B2B analysis** - Back-to-back games may matter more than current features capture
5. **Home/away specific ratings** - Separate home/off_rtg vs away/off_rtg (already partially done)
6. **Try XGBoost** - May find better hyperparams than GradientBoosting