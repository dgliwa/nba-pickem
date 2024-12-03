# NBA games : data collection & model creation
Initially inspired by this [kaggle project](https://www.kaggle.com/datasets/nathanlauga/nba-games). This repo hosts a few things:

* Collection of NBA game data
* Exploration of said nba game data
* Model generation to predict winners of nba games
  * Analysis of model performance with betting odds data to predict performance
* A web application that displays game winners for the current day (COMING SOON)

## Getting Started
Using [uv](https://docs.astral.sh/uv/) to manage dependencies.

```
uv sync
uv run jupyter server
```

This will kick off the jupyter notebook server to run and explore the data notebooks used to generate nba game winner predictions.

Advised that you start in `notebooks/00_init.ipynb`

## Data Collection

[scrapy](https://docs.scrapy.org/en/latest/index.html) is used to retrieve the team, game, and betting odds data.

Game data is collected from the [nba stats website](https://stats.nba.com/).
Odds data is collected from [sportsbookreview](https://www.sportsbookreview.com)

To collect the data you can run the `00_init.ipynb` notebook, or run scrapy commands for the various scrapers (NOTE: These can take a long time!)

ex: `uv run scrapy crawl nba_teams`

## Analysis

Model exploration happens in the `notebook` dir. Things like feature analysis, generation, model creation, profit calculation, etc is in these notebooks.

## Webapp Predictions

TODO

# Contributing

Check out the issues and milestones



