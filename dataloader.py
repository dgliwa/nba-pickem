import duckdb
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "nba_pickem.duckdb"


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


def recompute_features() -> pd.DataFrame:
    """Recompute features (b2b, last_10_win_pct) for all games in the database."""
    all_games = get_games()
    
    if all_games.empty:
        return all_games
    
    all_games = all_games.sort_values('game_date_est').reset_index(drop=True)
    
    b2b_home = []
    b2b_away = []
    last_10_home = []
    last_10_away = []
    
    for idx, game in all_games.iterrows():
        game_date = pd.to_datetime(game['game_date_est'])
        yesterday = game_date - pd.Timedelta(days=1)
        season = game['season']
        home_team = game['home_team_id']
        away_team = game['away_team_id']
        
        prior_games = all_games[all_games['game_date_est'] < game_date]
        
        home_played_yesterday = len(prior_games[
            (prior_games['game_date_est'] == yesterday) &
            ((prior_games['home_team_id'] == home_team) | (prior_games['away_team_id'] == home_team))
        ]) > 0
        
        away_played_yesterday = len(prior_games[
            (prior_games['game_date_est'] == yesterday) &
            ((prior_games['home_team_id'] == away_team) | (prior_games['away_team_id'] == away_team))
        ]) > 0
        
        b2b_home.append(bool(home_played_yesterday))
        b2b_away.append(bool(away_played_yesterday))
        
        prior_season = prior_games[prior_games['season'] == season]
        
        home_prior = prior_season[
            (prior_season['home_team_id'] == home_team) | (prior_season['away_team_id'] == home_team)
        ].sort_values('game_date_est').tail(10)
        
        if home_prior.empty:
            home_wpct = 0.5
        else:
            home_prior = home_prior.copy()
            home_prior['is_home'] = home_prior['home_team_id'] == home_team
            home_prior['won'] = home_prior['is_home'] == home_prior['home_team_wins']
            home_wpct = home_prior['won'].mean() if len(home_prior) > 0 else 0.5
        
        away_prior = prior_season[
            (prior_season['home_team_id'] == away_team) | (prior_season['away_team_id'] == away_team)
        ].sort_values('game_date_est').tail(10)
        
        if away_prior.empty:
            away_wpct = 0.5
        else:
            away_prior = away_prior.copy()
            away_prior['is_home'] = away_prior['home_team_id'] == away_team
            away_prior['won'] = away_prior['is_home'] == away_prior['home_team_wins']
            away_wpct = away_prior['won'].mean() if len(away_prior) > 0 else 0.5
        
        last_10_home.append(home_wpct)
        last_10_away.append(away_wpct)
    
    all_games['home_team_b2b'] = b2b_home
    all_games['away_team_b2b'] = b2b_away
    all_games['home_last_10_win_pct'] = last_10_home
    all_games['away_last_10_win_pct'] = last_10_away
    
    conn = get_connection()
    conn.execute("DELETE FROM games")
    conn.execute("ALTER TABLE games RENAME TO games_old")
    
    conn.execute("""
        CREATE TABLE games (
            game_id VARCHAR PRIMARY KEY,
            home_team_id VARCHAR,
            away_team_id VARCHAR,
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
    
    for _, row in all_games.iterrows():
        conn.execute("""
            INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            row['game_id'], row['home_team_id'], row['away_team_id'], row['game_date_est'], row['season'],
            row['home_team_points'], row['away_team_points'],
            None, None, None, None,
            row['home_last_10_win_pct'], row['away_last_10_win_pct'],
            row['home_team_b2b'], row['away_team_b2b'],
            row['home_team_wins']
        ])
    
    conn.execute("DROP TABLE games_old")
    conn.commit()
    conn.close()
    
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