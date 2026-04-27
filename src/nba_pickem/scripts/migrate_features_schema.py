#!/usr/bin/env python3
"""One-off migration script to fix the off_rtg/def_rtg/margin columns.

This script:
1. Renames existing off_rtg_*, def_rtg_*, margin_* columns to away_*
2. Adds new home_* columns
3. Recalculates all features for all seasons

Run with: python -m nba_pickem.scripts.migrate_features_schema
"""
import duckdb
from nba_pickem.config import DB_PATH
from nba_pickem.dataloader import recompute_all_features


def migrate():
    conn = duckdb.connect(str(DB_PATH))
    
    print("Step 1: Checking current schema...")
    cols = conn.execute("DESCRIBE games").fetchall()
    col_names = [c[0] for c in cols]
    print(f"  Current columns: {[c for c in col_names if 'rtg' in c or 'margin' in c]}")
    
    rename_map = {
        'off_rtg_5': 'away_off_rtg_5',
        'off_rtg_10': 'away_off_rtg_10',
        'def_rtg_5': 'away_def_rtg_5',
        'def_rtg_10': 'away_def_rtg_10',
        'margin_5': 'away_margin_5',
        'margin_10': 'away_margin_10',
    }
    
    existing_renames = {old: new for old, new in rename_map.items() if old in col_names}
    print(f"\nStep 2: Renaming {len(existing_renames)} columns...")
    for old_col, new_col in existing_renames.items():
        conn.execute(f"ALTER TABLE games RENAME {old_col} TO {new_col}")
        print(f"  {old_col} -> {new_col}")
    
    add_cols = [
        ('home_off_rtg_5', 'DECIMAL(6,2)'),
        ('home_off_rtg_10', 'DECIMAL(6,2)'),
        ('home_def_rtg_5', 'DECIMAL(6,2)'),
        ('home_def_rtg_10', 'DECIMAL(6,2)'),
        ('home_margin_5', 'DECIMAL(6,2)'),
        ('home_margin_10', 'DECIMAL(6,2)'),
    ]
    
    print(f"\nStep 3: Adding {len(add_cols)} new columns...")
    for col_name, col_type in add_cols:
        conn.execute(f"ALTER TABLE games ADD COLUMN {col_name} {col_type}")
        print(f"  Added {col_name}")
    
    conn.close()
    
    print(f"\nStep 4: Recomputing features for all seasons...")
    recompute_all_features(season=None)
    
    print("\n✓ Migration complete!")


if __name__ == "__main__":
    migrate()