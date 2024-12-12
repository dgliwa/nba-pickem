import logging
import scrapy

from datetime import datetime
from scraping.data import retrieve_games_df, retrieve_matchups_df

class NbaGamesSpider(scrapy.Spider):
    download_delay = 1.0
    name = "nba_games"
    allowed_domains = ["stats.nba.com"]
    start_urls = ["https://stats.nba.com"]

    HEADERS = {
        "Referer": "stats.nba.com",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Host": "stats.nba.com",
        "Origin": "https://stats.nba.com",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:70.0) Gecko/20100101 Firefox/70.0",
    }

    STARTING_YEAR = 2017

    def start_requests(self):
        self.log("initializing nba season games spider", level=logging.INFO)
        matchups = retrieve_matchups_df()
        games = retrieve_games_df()
        # breakpoint()

        if len(games):
            game_dates = matchups[~(matchups["GAME_DATE_EST"].isin(games["GAME_DATE_EST"].unique()))]["GAME_DATE_EST"].unique()
        else:
            game_dates = matchups["GAME_DATE_EST"].unique()


        for game_date in game_dates:
            game_date_formatted = game_date.strftime("%m/%d/%Y")
            url = f"https://stats.nba.com/stats/scoreboardV2?DayOffset=0&LeagueID=00&gameDate={game_date_formatted}&seasonType=RegularSeason"
            yield scrapy.Request(url=url, headers=self.HEADERS, callback=self.parse)


    def parse(self, response):
        jsonresponse = response.json()
        results = jsonresponse.get("resultSets")
        game_headers = results[0]
        game_scores = results[1]
        eastern_standings = results[4]
        western_standings = results[5]

        games = []
        for game in game_headers.get("rowSet"):
            game_id = game[2]
            home_team_id = game[6]
            away_team_id = game[7]
            season = game[8]
            game_score_home = next((score for score in game_scores.get("rowSet") if score[2] == game_id and score[3] == home_team_id))
            home_points = game_score_home[22]
            game_score_away = next((score for score in game_scores.get("rowSet") if score[2] == game_id and score[3] == away_team_id))
            away_points = game_score_away[22]
            home_team_wins = home_points > away_points

            if home_team_id in [r[0] for r in eastern_standings.get("rowSet")]:
                home_team_rank = next((team for team in eastern_standings.get("rowSet") if team[0] == home_team_id))
            else:
                home_team_rank = next((team for team in western_standings.get("rowSet") if team[0] == home_team_id))

            if away_team_id in [r[0] for r in eastern_standings.get("rowSet")]:
                away_team_rank = next((team for team in eastern_standings.get("rowSet") if team[0] == away_team_id))
            else:
                away_team_rank = next((team for team in western_standings.get("rowSet") if team[0] == away_team_id))

            home_win_pct = home_team_rank[9]
            home_home_wins, home_home_losses = home_team_rank[10].split("-")
            home_home_win_pct = int(home_home_wins) / (int(home_home_wins) + int(home_home_losses)) if int(home_home_wins) + int(home_home_losses) > 0 else 0

            away_win_pct = away_team_rank[9]
            away_away_wins, away_away_losses = away_team_rank[11].split("-")
            away_away_win_pct = int(away_away_wins) / (int(away_away_wins) + int(away_away_losses)) if int(away_away_wins) + int(away_away_losses) > 0 else 0


            games.append({
                "GAME_DATE_EST": datetime.strptime(game[0], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d"),
                "GAME_ID": game_id,
                "HOME_TEAM_ID": home_team_id,
                "AWAY_TEAM_ID": away_team_id,
                "SEASON": season,
                "HOME_TEAM_POINTS": home_points,
                "AWAY_TEAM_POINTS": away_points,
                "HOME_WIN_PCT": home_win_pct,
                "HOME_HOME_WIN_PCT": home_home_win_pct,
                "AWAY_WIN_PCT": away_win_pct,
                "AWAY_AWAY_WIN_PCT": away_away_win_pct,
                "HOME_TEAM_WINS": home_team_wins,
            })
        return games
