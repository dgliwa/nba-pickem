.PHONY: install init extract predict jupyter clean

install:
	uv sync

init:
	uv run python -c "from dataloader import init_db; init_db()"

extract:
	uv run python scripts/run_extraction.py

extract-teams:
	uv run python scripts/run_extraction.py --teams

extract-games:
	uv run python scripts/run_extraction.py --games

extract-matchups:
	uv run python scripts/run_extraction.py --matchups

extract-odds:
	uv run python scripts/run_extraction.py --odds

predict:
	uv run python scripts/run_prediction.py

predict-date:
	$(eval DATE = $(shell date +%Y-%m-%d))
	uv run python scripts/run_prediction.py $(DATE)

jupyter:
	uv run jupyter notebook

clean:
	rm -f data/nba_pickem.duckdb
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true