import pandas as pd
import os

def prep_nba_games():
    """
    Prepares NBA games data for further processing.

    """
    if not os.path.exists("data/nba_teams.csv"):
        raise "No NBA teams data found. Please run the NBA teams spider first."

    teams = pd.read_csv("data/nba_teams.csv")

    if not os.path.exists("data/raw/nba_games.csv"):
        raise "No NBA games data found. Please run the NBA games spider first."

    nba_games = pd.read_csv("data/raw/nba_games.csv")
    nba_games = nba_games.sort_values(by="GAME_DATE_EST")

    home_game_data = []
    away_game_data = []
    for team in teams["TEAM_ID"]:
      print(f"Processing team {team}...")
      team_games = nba_games[(nba_games["HOME_TEAM_ID"] == team) | (nba_games["AWAY_TEAM_ID"] == team)]
      team_games["GAME_DATE_EST"] = pd.to_datetime(team_games["GAME_DATE_EST"])

      for _, game in team_games.iterrows():
        previous_games = team_games[(team_games["GAME_DATE_EST"] < game["GAME_DATE_EST"]) & (team_games["SEASON"] == game["SEASON"])]
        previous_home_games = previous_games[previous_games["HOME_TEAM_ID"] == team]
        previous_away_games = previous_games[previous_games["AWAY_TEAM_ID"] == team]
        previous_won_home_games = previous_home_games[previous_home_games["HOME_TEAM_WINS"]]
        previous_won_away_games = previous_away_games[~previous_away_games["HOME_TEAM_WINS"]]


        if game["HOME_TEAM_ID"] == team:
          home_game_data.append({
            "GAME_ID": game["GAME_ID"],
            "HOME_WIN_PCT": (len(previous_won_home_games) + len(previous_won_away_games)) / len(previous_games) if len(previous_games) > 0 else 0,
            "HOME_WIN_PCT_AT_HOME": len(previous_won_home_games) / len(previous_home_games) if len(previous_home_games) > 0 else 0,
          })
        else:
          away_game_data.append({
            "GAME_ID": game["GAME_ID"],
            "AWAY_WIN_PCT": (len(previous_won_home_games) + len(previous_won_away_games)) / len(previous_games) if len(previous_games) > 0 else 0,
            "AWAY_WIN_PCT_AWAY": len(previous_won_away_games) / len(previous_away_games) if len(previous_away_games) > 0 else 0
          })

    home_game_data_df = pd.DataFrame(home_game_data)
    away_game_data_df = pd.DataFrame(away_game_data)
    game_data_df = home_game_data_df.merge(away_game_data_df, how="inner", on="GAME_ID")

    nba_games = nba_games.merge(game_data_df, how="inner", on="GAME_ID")
    nba_games.to_csv("data/nba_games.csv", index=False)




if __name__ == "__main__":
    prep_nba_games()
