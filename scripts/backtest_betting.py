#!/usr/bin/env python3
"""Walk-forward moneyline betting backtest.

For each test season, fit the production model on every earlier season from 2016, then bet
games where the model's probability beats the market's (bookmaker margin removed) by at least
an edge threshold. Flat 1-unit stakes.

Two entry points:
- open:  bet at the opening line. Prices are the best open price across books, or the median
         book's ("consensus"). Openers can be posted before the previous night's results, which
         Elo has already absorbed, so this can flatter the model slightly.
- close: bet at the closing line (just before tip). No look-ahead, but the hardest market.

CLV (closing line value) = closing no-margin probability of the side bet minus the probability
implied by the price taken. Positive CLV means the market moved toward our bet.

Usage:
    uv run python scripts/backtest_betting.py
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from nba_pickem.dataloader import get_connection, get_games
from nba_pickem.features import MODEL_FEATURES, add_matchup_diffs

TRAIN_START = 2016
TEST_SEASONS = range(2020, 2027)
THRESHOLDS = (0.0, 0.02, 0.04, 0.06, 0.08, 0.10)


def decimal(american: pd.Series) -> pd.Series:
    american = american.astype(float)
    return np.where(american > 0, 1 + american / 100, 1 + 100 / -american)


def market_lines() -> pd.DataFrame:
    """Per game: consensus no-margin home probability (open, close) and prices per side."""
    conn = get_connection()
    odds = conn.execute("""
        SELECT game_id, sportsbook, open_home_odds, open_away_odds, latest_home_odds, latest_away_odds
        FROM moneylines
    """).df()
    conn.close()
    for when in ('open', 'latest'):
        odds[f'{when}_home_dec'] = decimal(odds[f'{when}_home_odds'])
        odds[f'{when}_away_dec'] = decimal(odds[f'{when}_away_odds'])
        implied_home, implied_away = 1 / odds[f'{when}_home_dec'], 1 / odds[f'{when}_away_dec']
        overround = implied_home + implied_away
        sane = (overround > 1.0) & (overround < 1.12)  # drop arbitrage-looking or stale one-off lines
        odds.loc[~sane, [f'{when}_home_dec', f'{when}_away_dec']] = np.nan
        odds[f'{when}_home_fair'] = (implied_home / overround).where(sane)
    grouped = odds.groupby('game_id')
    return pd.DataFrame({
        'books': grouped.size(),
        'open_fair': grouped['open_home_fair'].median(),
        'close_fair': grouped['latest_home_fair'].median(),
        'open_home_best': grouped['open_home_dec'].max(),
        'open_away_best': grouped['open_away_dec'].max(),
        'open_home_median': grouped['open_home_dec'].median(),
        'open_away_median': grouped['open_away_dec'].median(),
        'close_home_best': grouped['latest_home_dec'].max(),
        'close_away_best': grouped['latest_away_dec'].max(),
    }).reset_index()


def model_probabilities(games: pd.DataFrame) -> pd.DataFrame:
    out = []
    for season in TEST_SEASONS:
        train = games[games['season'].between(TRAIN_START, season - 1)]
        test = games[games['season'] == season].copy()
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
        model.fit(train[MODEL_FEATURES], train['home_team_wins'].astype(int))
        test['p_model'] = model.predict_proba(test[MODEL_FEATURES])[:, 1]
        out.append(test)
    return pd.concat(out)


def bets(df: pd.DataFrame, market: str, price: str, threshold: float) -> pd.DataFrame:
    """`price` is a column template like 'open_{}_best', filled with 'home' or 'away'."""
    # One bet per game on the side whose model edge over the `market` probability is >= threshold
    home_edge = df['p_model'] - df[f'{market}_fair']
    away_edge = -home_edge
    side_home = home_edge >= away_edge
    edge = np.where(side_home, home_edge, away_edge)
    b = df.assign(side_home=side_home, edge=edge)
    b = b[(b['edge'] >= threshold) & b[price.format('home')].notna()].copy()
    b['price'] = np.where(b['side_home'], b[price.format('home')], b[price.format('away')])
    b['won'] = b['side_home'] == b['home_team_wins'].astype(bool)
    b['profit'] = np.where(b['won'], b['price'] - 1, -1.0)
    close_side = np.where(b['side_home'], b['close_fair'], 1 - b['close_fair'])
    b['clv'] = close_side - 1 / b['price']
    return b


def summarize(b: pd.DataFrame) -> dict:
    n = len(b)
    if n == 0:
        return {'bets': 0}
    roi = b['profit'].mean()
    return {
        'bets': n,
        'win_rate': b['won'].mean(),
        'avg_price': b['price'].mean(),
        'roi': roi,
        'roi_se': b['profit'].std(ddof=1) / np.sqrt(n),
        'clv': b['clv'].mean(),  # over bets whose game has a closing line
        'pos_seasons': f"{int((b.groupby('season')['profit'].sum() > 0).sum())}/{b['season'].nunique()}",
    }


def main():
    games = add_matchup_diffs(get_games(played_only=True))
    df = model_probabilities(games).merge(market_lines(), on='game_id')
    print(f"{len(df)} games with odds, seasons {min(TEST_SEASONS)}-{max(TEST_SEASONS)}; "
          f"model trained walk-forward from {TRAIN_START}")

    both = df.dropna(subset=['open_fair', 'close_fair'])
    y = both['home_team_wins'].astype(int)
    print(f"  {len(both)} games with both an opening and a closing line:")
    for label, p in (('model', both['p_model']), ('open market', both['open_fair']), ('close market', both['close_fair'])):
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        acc = ((p >= .5) == y.astype(bool)).mean()
        print(f"  {label:13} log-loss {ll:.4f}  accuracy {acc:.4f}")

    scenarios = {
        'open, best price': ('open', 'open_{}_best'),
        'open, consensus price': ('open', 'open_{}_median'),
        'close, best price': ('close', 'close_{}_best'),
    }
    for label, (market, price) in scenarios.items():
        rows = [{'edge>=': t, **summarize(bets(df, market, price, t))} for t in THRESHOLDS]
        print(f"\n=== bet at {label} (edge vs {market} consensus, flat 1u) ===")
        print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    for label, (market, price) in scenarios.items():
        b = bets(df, market, price, 0.04)
        by_season = pd.DataFrame({season: summarize(s) for season, s in b.groupby('season')}).T
        print(f"\n=== by season: {label}, edge >= 4% ===")
        print(by_season[['bets', 'win_rate', 'roi', 'clv']].to_string())


if __name__ == "__main__":
    main()
