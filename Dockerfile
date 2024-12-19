FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG CELERY_BROKER_URL
RUN echo "CELERY_BROKER_URL=$CELERY_BROKER_URL"

# Change the working directory to the `app` directory
WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

ADD alembic.ini /app/alembic.ini
ADD ./dao /app/dao
ADD ./db /app/db
ADD ./scrapy.cfg /app/scrapy.cfg
ADD ./web /app/web
ADD ./worker /app/worker
ADD ./services /app/services
ADD ./scraping /app/scraping
ADD ./pyproject.toml /app
ADD ./uv.lock /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# TODO: Eventually replace this with a process to seed a db
ADD ./data/raw/nba_teams.csv /app/data/raw/nba_teams.csv
RUN test -f /app/data/raw/nba_teams.csv 