import duckdb
import pandas as pd

from .config import DB_PATH


def get_connection():
    return duckdb.connect(str(DB_PATH))


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER,
            league_id INTEGER,
            abbreviation VARCHAR,
            city VARCHAR,
            nickname VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id VARCHAR PRIMARY KEY,
            home_team_id INTEGER,
            away_team_id INTEGER,
            game_date_est DATE,
            season INTEGER,
            home_team_points INTEGER,
            away_team_points INTEGER,
            home_win_pct DECIMAL(5,4),
            home_home_win_pct DECIMAL(5,4),
            away_win_pct DECIMAL(5,4),
            away_away_win_pct DECIMAL(5,4),
            home_last_10_win_pct DECIMAL(5,4),
            away_last_10_win_pct DECIMAL(5,4),
            home_team_b2b BOOLEAN,
            away_team_b2b BOOLEAN,
            home_team_wins BOOLEAN
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS game_predictions (
            game_id VARCHAR PRIMARY KEY,
            home_team_id INTEGER,
            away_team_id INTEGER,
            predicted_home_team_wins BOOLEAN,
            game_date_est DATE,
            home_win_pct DECIMAL(5,4),
            home_home_win_pct DECIMAL(5,4),
            away_win_pct DECIMAL(5,4),
            away_away_win_pct DECIMAL(5,4),
            home_last_10_win_pct DECIMAL(5,4),
            away_last_10_win_pct DECIMAL(5,4),
            home_team_b2b BOOLEAN,
            away_team_b2b BOOLEAN
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS moneyline_odds (
            id INTEGER PRIMARY KEY,
            game_id VARCHAR,
            sportsbook VARCHAR,
            home_odds INTEGER,
            away_odds INTEGER,
            game_date_est DATE,
            line_datetime TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seasons (
            season_year INTEGER PRIMARY KEY,
            is_regular_season_complete BOOLEAN DEFAULT FALSE,
            playoffs_start_date DATE,
            last_extract_at TIMESTAMP,
            games_loaded INTEGER DEFAULT 0
        )
    """)
    conn.close()


def get_teams() -> pd.DataFrame:
    conn = get_connection()
    df = conn.execute("SELECT * FROM teams").df()
    conn.close()
    return df


def save_teams(teams_df: pd.DataFrame):
    conn = get_connection()
    conn.execute("DELETE FROM teams")
    conn.execute("INSERT INTO teams SELECT * FROM teams_df")
    conn.close()


def get_games(start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    conn = get_connection()
    query = "SELECT * FROM games"
    conditions = []
    if start_date:
        conditions.append(f"game_date_est >= '{start_date}'")
    if end_date:
        conditions.append(f"game_date_est <= '{end_date}'")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    df = conn.execute(query + " ORDER BY game_date_est").df()
    conn.close()
    if not df.empty and 'game_date_est' in df.columns:
        df['game_date_est'] = pd.to_datetime(df['game_date_est'])
    return df


def recompute_features(season: int) -> pd.DataFrame:
    """Recompute features for games in a season.
    
    DEPRECATED: Use recompute_all_features() instead for all seasons.
    
    Args:
        season: The season year to recompute features for (e.g., 2025 for 2025-2026)
    """
    return recompute_all_features(season=season)


def recompute_all_features(season: int | None = None) -> pd.DataFrame:
    """Recompute ALL features (b2b, win%, off_rtg, def_rtg, rest_days, home/away splits).
    
    Computes rolling features using as-of logic (only games BEFORE the current game).
    
    Args:
        season: Specific season to recompute, or None for all seasons
    """
    all_games = get_games()
    
    if all_games.empty:
        return all_games
    
    if season:
        all_games = all_games[all_games['season'] == season].copy()
        if all_games.empty:
            return all_games
    
    return _compute_features_internal(all_games)


def _compute_features_internal(all_games: pd.DataFrame) -> pd.DataFrame:
    """Internal function to compute all rolling features."""
    all_games = all_games.sort_values('game_date_est').reset_index(drop=True)
    
    n_values = [5, 10]
    
    for n in n_values:
        all_games[f'home_win_pct_{n}'] = 0.5
        all_games[f'away_win_pct_{n}'] = 0.5
        all_games[f'home_off_rtg_{n}'] = 100.0
        all_games[f'home_def_rtg_{n}'] = 100.0
        all_games[f'home_margin_{n}'] = 0.0
        all_games[f'away_off_rtg_{n}'] = 100.0
        all_games[f'away_def_rtg_{n}'] = 100.0
        all_games[f'away_margin_{n}'] = 0.0
    
    all_games['rest_days'] = 0
    all_games['home_wpct_home'] = 0.5
    all_games['away_wpct_away'] = 0.5
    
    lookup_games = all_games.sort_values('game_date_est')
    
    print(f"Computing features for {len(all_games)} games...")
    
    for idx, game in all_games.iterrows():
        game_date = pd.to_datetime(game['game_date_est'])
        game_season = game['season']
        home_team = game['home_team_id']
        away_team = game['away_team_id']
        
        prior_mask = (lookup_games['game_date_est'] < game_date) & (lookup_games['season'] == game_season)
        prior_games = lookup_games[prior_mask].copy()
        
        same_season_prior = prior_games[prior_games['season'] == game_season]
        
        yesterday = game_date - pd.Timedelta(days=1)
        
        home_last_game = prior_games[
            (prior_games['home_team_id'] == home_team) | (prior_games['away_team_id'] == home_team)
        ].sort_values('game_date_est').tail(1)
        away_last_game = prior_games[
            (prior_games['home_team_id'] == away_team) | (prior_games['away_team_id'] == away_team)
        ].sort_values('game_date_est').tail(1)
        
        home_rest = (game_date - pd.to_datetime(home_last_game['game_date_est']).iloc[0]).days if not home_last_game.empty else 7
        away_rest = (game_date - pd.to_datetime(away_last_game['game_date_est']).iloc[0]).days if not away_last_game.empty else 7
        
        all_games.at[idx, 'rest_days'] = max(home_rest, away_rest)
        
        for n in n_values:
            home_team_prior = same_season_prior[
                (same_season_prior['home_team_id'] == home_team) | (same_season_prior['away_team_id'] == home_team)
            ].sort_values('game_date_est').tail(n)
            
            away_team_prior = same_season_prior[
                (same_season_prior['home_team_id'] == away_team) | (same_season_prior['away_team_id'] == away_team)
            ].sort_values('game_date_est').tail(n)
            
            if not home_team_prior.empty:
                home_team_prior_copy = home_team_prior.copy()
                home_team_prior_copy['is_home'] = home_team_prior_copy['home_team_id'] == home_team
                home_team_prior_copy['won'] = home_team_prior_copy['is_home'] == home_team_prior_copy['home_team_wins']
                all_games.at[idx, f'home_win_pct_{n}'] = home_team_prior_copy['won'].mean() if len(home_team_prior_copy) > 0 else 0.5
                
                home_team_prior_copy['pts_for'] = home_team_prior_copy.apply(
                    lambda r: r['home_team_points'] if r['home_team_id'] == home_team else r['away_team_points'], axis=1
                )
                all_games.at[idx, f'home_off_rtg_{n}'] = home_team_prior_copy['pts_for'].mean() if len(home_team_prior_copy) > 0 else 100.0
                
                home_team_prior_copy['pts_against'] = home_team_prior_copy.apply(
                    lambda r: r['away_team_points'] if r['home_team_id'] == home_team else r['home_team_points'], axis=1
                )
                all_games.at[idx, f'home_def_rtg_{n}'] = home_team_prior_copy['pts_against'].mean() if len(home_team_prior_copy) > 0 else 100.0
                
                home_team_prior_copy['margin'] = home_team_prior_copy['pts_for'] - home_team_prior_copy['pts_against']
                all_games.at[idx, f'home_margin_{n}'] = home_team_prior_copy['margin'].mean() if len(home_team_prior_copy) > 0 else 0.0
            
            if not away_team_prior.empty:
                away_team_prior_copy = away_team_prior.copy()
                away_team_prior_copy['is_home'] = away_team_prior_copy['home_team_id'] == away_team
                away_team_prior_copy['won'] = away_team_prior_copy['is_home'] == away_team_prior_copy['home_team_wins']
                all_games.at[idx, f'away_win_pct_{n}'] = away_team_prior_copy['won'].mean() if len(away_team_prior_copy) > 0 else 0.5
                
                away_team_prior_copy['pts_for'] = away_team_prior_copy.apply(
                    lambda r: r['home_team_points'] if r['home_team_id'] == away_team else r['away_team_points'], axis=1
                )
                all_games.at[idx, f'away_off_rtg_{n}'] = away_team_prior_copy['pts_for'].mean() if len(away_team_prior_copy) > 0 else 100.0
                
                away_team_prior_copy['pts_against'] = away_team_prior_copy.apply(
                    lambda r: r['away_team_points'] if r['home_team_id'] == away_team else r['home_team_points'], axis=1
                )
                all_games.at[idx, f'away_def_rtg_{n}'] = away_team_prior_copy['pts_against'].mean() if len(away_team_prior_copy) > 0 else 100.0
                
                away_team_prior_copy['margin'] = away_team_prior_copy['pts_for'] - away_team_prior_copy['pts_against']
                all_games.at[idx, f'away_margin_{n}'] = away_team_prior_copy['margin'].mean() if len(away_team_prior_copy) > 0 else 0.0
        
        home_home_games = same_season_prior[same_season_prior['home_team_id'] == home_team].sort_values('game_date_est').tail(10)
        away_away_games = same_season_prior[same_season_prior['away_team_id'] == away_team].sort_values('game_date_est').tail(10)
        
        if not home_home_games.empty:
            all_games.at[idx, 'home_wpct_home'] = home_home_games['home_team_wins'].mean()
        if not away_away_games.empty:
            all_games.at[idx, 'away_wpct_away'] = away_away_games.apply(
                lambda r: not r['home_team_wins'], axis=1
            ).mean()
        
        if idx % 500 == 0:
            print(f"  Processed {idx}/{len(all_games)} games...")
    
    # Update existing rows with computed features
    conn = get_connection()
    
    has_table = conn.execute("SELECT table_name FROM duckdb_tables() WHERE table_name = 'games'").fetchone()
    if not has_table:
        # Create table if it doesn't exist
        conn.execute("""
        CREATE TABLE games (
            game_id VARCHAR PRIMARY KEY,
            home_team_id VARCHAR,
            away_team_id VARCHAR,
            game_date_est DATE,
            season INTEGER,
            home_team_points INTEGER,
            away_team_points INTEGER,
            home_win_pct_5 DECIMAL(5,4),
            home_win_pct_10 DECIMAL(5,4),
            away_win_pct_5 DECIMAL(5,4),
            away_win_pct_10 DECIMAL(5,4),
            home_off_rtg_5 DECIMAL(6,2),
            home_off_rtg_10 DECIMAL(6,2),
            home_def_rtg_5 DECIMAL(6,2),
            home_def_rtg_10 DECIMAL(6,2),
            home_margin_5 DECIMAL(6,2),
            home_margin_10 DECIMAL(6,2),
            away_off_rtg_5 DECIMAL(6,2),
            away_off_rtg_10 DECIMAL(6,2),
            away_def_rtg_5 DECIMAL(6,2),
            away_def_rtg_10 DECIMAL(6,2),
            away_margin_5 DECIMAL(6,2),
            away_margin_10 DECIMAL(6,2),
            rest_days INTEGER,
            home_wpct_home DECIMAL(5,4),
            away_wpct_away DECIMAL(5,4),
            home_team_b2b BOOLEAN,
            away_team_b2b BOOLEAN,
            home_team_wins BOOLEAN
        )
    """)
    
    # UPDATE existing rows with computed features instead of dropping
    def _val(row, col, default):
        val = row.get(col, default)
        if pd.isna(val):
            return default
        return val
    
    for _, row in all_games.iterrows():
        conn.execute("""
            UPDATE games SET 
                home_win_pct_5 = ?, home_win_pct_10 = ?,
                away_win_pct_5 = ?, away_win_pct_10 = ?,
                home_off_rtg_5 = ?, home_off_rtg_10 = ?,
                home_def_rtg_5 = ?, home_def_rtg_10 = ?,
                home_margin_5 = ?, home_margin_10 = ?,
                away_off_rtg_5 = ?, away_off_rtg_10 = ?,
                away_def_rtg_5 = ?, away_def_rtg_10 = ?,
                away_margin_5 = ?, away_margin_10 = ?,
                rest_days = ?,
                home_wpct_home = ?, away_wpct_away = ?
            WHERE game_id = ?
        """, [
            _val(row, 'home_win_pct_5', 0.5), _val(row, 'home_win_pct_10', 0.5),
            _val(row, 'away_win_pct_5', 0.5), _val(row, 'away_win_pct_10', 0.5),
            _val(row, 'home_off_rtg_5', 100.0), _val(row, 'home_off_rtg_10', 100.0),
            _val(row, 'home_def_rtg_5', 100.0), _val(row, 'home_def_rtg_10', 100.0),
            _val(row, 'home_margin_5', 0.0), _val(row, 'home_margin_10', 0.0),
            _val(row, 'away_off_rtg_5', 100.0), _val(row, 'away_off_rtg_10', 100.0),
            _val(row, 'away_def_rtg_5', 100.0), _val(row, 'away_def_rtg_10', 100.0),
            _val(row, 'away_margin_5', 0.0), _val(row, 'away_margin_10', 0.0),
            int(_val(row, 'rest_days', 3)),
            _val(row, 'home_wpct_home', 0.5), _val(row, 'away_wpct_away', 0.5),
            row['game_id']
        ])
    
    conn.commit()
    conn.close()
    
    print(f"Features computed for {len(all_games)} games!")
    return all_games


def save_games(games_df: pd.DataFrame):
    games_df = preprocess_games(games_df)
    
    col_map = {
        "GAME_ID": "game_id", "HOME_TEAM_ID": "home_team_id", "AWAY_TEAM_ID": "away_team_id",
        "GAME_DATE_EST": "game_date_est", "SEASON": "season",
        "HOME_TEAM_POINTS": "home_team_points", "AWAY_TEAM_POINTS": "away_team_points",
        "HOME_WIN_PCT": "home_win_pct", "HOME_HOME_WIN_PCT": "home_home_win_pct",
        "AWAY_WIN_PCT": "away_win_pct", "AWAY_AWAY_WIN_PCT": "away_away_win_pct",
        "HOME_LAST_10_WIN_PCT": "home_last_10_win_pct", "AWAY_LAST_10_WIN_PCT": "away_last_10_win_pct",
        "HOME_TEAM_B2B": "home_team_b2b", "AWAY_TEAM_B2B": "away_team_b2b",
        "HOME_TEAM_WINS": "home_team_wins"
    }
    df = games_df.rename(columns=col_map)[list(col_map.values())]
    conn = get_connection()
    conn.execute("DELETE FROM games")
    cols = ", ".join(df.columns)
    conn.execute(f"INSERT INTO games ({cols}) SELECT * FROM df")
    conn.close()


def preprocess_games(games_df: pd.DataFrame) -> pd.DataFrame:
    """Combine new games with existing, calculate features (B2B, last_10_win_pct)."""
    games_df = games_df.copy()
    
    # Normalize column names to lowercase for consistency
    games_df.columns = games_df.columns.str.lower()
    
    # Ensure date column is datetime
    if 'game_date_est' in games_df.columns:
        games_df['game_date_est'] = pd.to_datetime(games_df['game_date_est'])
    elif 'GAME_DATE_EST' in games_df.columns:
        games_df['game_date_est'] = pd.to_datetime(games_df['GAME_DATE_EST'])
    
    existing = get_games()
    
    init_features = {
        'home_team_b2b': False, 'away_team_b2b': False,
        'home_last_10_win_pct': 0.0, 'away_last_10_win_pct': 0.0
    }
    for col, val in init_features.items():
        if col not in games_df.columns:
            games_df[col] = val
    
    if existing.empty:
        # No existing games - use games_df itself as history (for initial bulk load)
        all_games = games_df.sort_values('game_date_est')
    else:
        existing['game_date_est'] = pd.to_datetime(existing['game_date_est'])
        all_games = pd.concat([games_df, existing]).sort_values('game_date_est')
    
    games_df = calculate_b2b(games_df, all_games)
    games_df = calculate_last_n_win_pct(games_df, all_games, n=10)
    
    return games_df


def calculate_b2b(games_df: pd.DataFrame, all_games: pd.DataFrame) -> pd.DataFrame:
    """Calculate HOME_TEAM_B2B and AWAY_TEAM_B2B (played yesterday?)."""
    b2b_home = []
    b2b_away = []
    
    for _, game in games_df.iterrows():
        game_date = pd.to_datetime(game['game_date_est'])
        yesterday = game_date - pd.Timedelta(days=1)
        
        home_team = game['home_team_id']
        away_team = game['away_team_id']
        
        home_played_yesterday = len(all_games[
            (all_games['game_date_est'].dt.date == yesterday.date()) &
            ((all_games['home_team_id'] == home_team) | (all_games['away_team_id'] == home_team))
        ]) > 0
        
        away_played_yesterday = len(all_games[
            (all_games['game_date_est'].dt.date == yesterday.date()) &
            ((all_games['home_team_id'] == away_team) | (all_games['away_team_id'] == away_team))
        ]) > 0
        
        b2b_home.append(bool(home_played_yesterday))
        b2b_away.append(bool(away_played_yesterday))
    
    games_df['home_team_b2b'] = b2b_home
    games_df['away_team_b2b'] = b2b_away
    
    return games_df


def calculate_last_n_win_pct(games_df: pd.DataFrame, all_games: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Calculate rolling N-game win pct, respecting season boundaries."""
    last_10_home = []
    last_10_away = []
    
    for _, game in games_df.iterrows():
        game_date = pd.to_datetime(game['game_date_est'])
        season = game['season']
        home_team = game['home_team_id']
        away_team = game['away_team_id']
        
        prior_games = all_games[
            (all_games['game_date_est'] < game_date) &
            (all_games['season'] == season) &
            ((all_games['home_team_id'] == home_team) | (all_games['away_team_id'] == home_team))
        ].sort_values('game_date_est').tail(n)
        
        if prior_games.empty:
            home_win_pct = 0.0
        else:
            prior_games = prior_games.copy()
            prior_games['is_home'] = prior_games['home_team_id']== home_team
            prior_games['won'] = prior_games['is_home'] == prior_games['home_team_wins']
            home_win_pct = prior_games['won'].mean()
        
        prior_games = all_games[
            (all_games['game_date_est'] < game_date) &
            (all_games['season'] == season) &
            ((all_games['home_team_id'] == away_team) | (all_games['away_team_id'] == away_team))
        ].sort_values('game_date_est').tail(n)
        
        if prior_games.empty:
            away_win_pct = 0.0
        else:
            prior_games = prior_games.copy()
            prior_games['is_home'] = prior_games['home_team_id']== away_team
            prior_games['won'] = prior_games['is_home'] == prior_games['home_team_wins']
            away_win_pct = prior_games['won'].mean()
        
        last_10_home.append(home_win_pct)
        last_10_away.append(away_win_pct)
    
    games_df['home_last_10_win_pct'] = last_10_home
    games_df['away_last_10_win_pct'] = last_10_away
    
    return games_df


def get_predictions(game_date: str | None = None) -> pd.DataFrame:
    conn = get_connection()
    query = "SELECT * FROM game_predictions"
    if game_date:
        query += f" WHERE game_date_est = '{game_date}'"
    df = conn.execute(query).df()
    conn.close()
    if not df.empty and 'game_date_est' in df.columns:
        df['game_date_est'] = pd.to_datetime(df['game_date_est'])
    return df


def save_predictions(predictions_df: pd.DataFrame):
    conn = get_connection()
    df = predictions_df.rename(columns=str.lower)
    temp_table = "temp_preds"
    conn.execute(f"CREATE TABLE {temp_table} AS SELECT * FROM game_predictions WHERE 1=0")
    conn.execute(f"INSERT INTO {temp_table} SELECT * FROM df")
    conn.execute(f"""
        MERGE INTO game_predictions g
        USING {temp_table} t
        ON g.game_id = t.game_id
        WHEN MATCHED THEN UPDATE SET
            predicted_home_team_wins = t.predicted_home_team_wins
        WHEN NOT MATCHED THEN INSERT *
    """)
    conn.execute(f"DROP TABLE {temp_table}")
    conn.close()


def get_moneylines(game_date: str | None = None, sportsbook: str | None = None) -> pd.DataFrame:
    conn = get_connection()
    query = "SELECT * FROM moneyline_odds"
    conditions = []
    if game_date:
        conditions.append(f"game_date_est = '{game_date}'")
    if sportsbook:
        conditions.append(f"sportsbook = '{sportsbook}'")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    df = conn.execute(query).df()
    conn.close()
    return df


def save_moneylines(moneylines_df: pd.DataFrame):
    conn = get_connection()
    conn.execute("""
        INSERT INTO moneyline_odds (game_id, sportsbook, home_odds, away_odds, game_date_est, line_datetime)
        VALUES (:game_id, :sportsbook, :home_odds, :away_odds, :game_date_est, :line_datetime)
    """, moneylines_df.to_dicts())
    conn.close()


def get_todays_games() -> pd.DataFrame:
    conn = get_connection()
    df = conn.execute("""
        SELECT g.*, t_home.abbreviation as home_team, t_away.abbreviation as away_team
        FROM games g
        JOIN teams t_home ON g.home_team_id = t_home.team_id
        JOIN teams t_away ON g.away_team_id = t_away.team_id
        WHERE g.game_date_est = CURRENT_DATE
    """).df()
    conn.close()
    return df


def get_prediction_accuracy() -> dict:
    conn = get_connection()
    result = conn.execute("""
        SELECT
            COUNT(*) as total_games,
            SUM(CASE WHEN gp.predicted_home_team_wins = g.home_team_wins THEN 1 ELSE 0 END) as correct,
            ROUND(100.0 * SUM(CASE WHEN gp.predicted_home_team_wins = g.home_team_wins THEN 1 ELSE 0 END) / COUNT(*), 1) as accuracy_pct
        FROM game_predictions gp
        JOIN games g ON gp.game_id = g.game_id
        WHERE g.home_team_points IS NOT NULL
    """).fetchone()
    conn.close()
    return {"total_games": result[0], "correct": result[1], "accuracy_pct": result[2]}


def seed_seasons_from_games():
    """Seed seasons table from existing games data."""
    conn = get_connection()
    # A full regular season has ~1230 games, use 1200 as threshold
    MIN_GAMES_FOR_COMPLETE = 1200
    conn.execute("""
        INSERT OR REPLACE INTO seasons (season_year, games_loaded, is_regular_season_complete)
        SELECT 
            season, 
            COUNT(*) as games_loaded,
            CASE WHEN COUNT(*) >= ? THEN TRUE ELSE FALSE END as is_regular_season_complete
        FROM games 
        GROUP BY season
    """, [MIN_GAMES_FOR_COMPLETE])
    conn.commit()
    conn.close()


def get_incomplete_seasons() -> list:
    """Get list of incomplete seasons."""
    conn = get_connection()
    result = conn.execute("""
        SELECT season_year FROM seasons 
        WHERE is_regular_season_complete = FALSE 
        ORDER BY season_year DESC
    """).fetchall()
    conn.close()
    return [r[0] for r in result]


def get_current_season() -> int | None:
    """Get the current (most recent incomplete) season."""
    conn = get_connection()
    result = conn.execute("""
        SELECT season_year FROM seasons 
        WHERE is_regular_season_complete = FALSE 
        ORDER BY season_year DESC 
        LIMIT 1
    """).fetchone()
    conn.close()
    return result[0] if result else None


def has_teams() -> bool:
    """Check if teams are loaded."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    conn.close()
    return count > 0


def mark_season_complete(season_year: int):
    """Mark a season as complete."""
    conn = get_connection()
    conn.execute("""
        UPDATE seasons 
        SET is_regular_season_complete = TRUE 
        WHERE season_year = ?
    """, [season_year])
    conn.commit()
    conn.close()


def update_season_games_count(season_year: int):
    """Update the games_loaded count for a season."""
    conn = get_connection()
    count = conn.execute("""
        SELECT COUNT(*) FROM games WHERE season = ?
    """, [season_year]).fetchone()[0]
    conn.execute("""
        UPDATE seasons SET games_loaded = ?, last_extract_at = CURRENT_TIMESTAMP 
        WHERE season_year = ?
    """, [count, season_year])
    conn.commit()
    conn.close()


def get_season_games_count(season_year: int) -> int:
    """Get the count of games for a season."""
    conn = get_connection()
    count = conn.execute("""
        SELECT COUNT(*) FROM games WHERE season = ?
    """, [season_year]).fetchone()[0]
    conn.close()
    return count