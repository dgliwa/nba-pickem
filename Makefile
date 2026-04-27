.PHONY: install init extract extract-teams extract-games predict jupyter clean

install:
	uv pip install -e .

init:
	nba-pickem-init

init-load:
	nba-pickem-init --load

extract:
	nba-pickem-extract

extract-teams:
	nba-pickem-extract --teams

extract-games:
	nba-pickem-extract --games

predict:
	nba-pickem-predict

predict-date:
	nba-pickem-predict $(shell date +%Y-%m-%d)

jupyter:
	uv run jupyter notebook

clean:
	rm -f data/nba_pickem.duckdb
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true