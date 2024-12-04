from fasthtml import FastHTML
from fasthtml.common import *

app = FastHTML(hdrs=picolink)

GAMES = [
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"CHA","NICKNAME_HOME":"Hornets","ABBREVIATION_AWAY":"PHI","NICKNAME_AWAY":"76ers","WINNER":"PHI 76ers"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"CLE","NICKNAME_HOME":"Cavaliers","ABBREVIATION_AWAY":"WAS","NICKNAME_AWAY":"Wizards","WINNER":"CLE Cavaliers"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"DET","NICKNAME_HOME":"Pistons","ABBREVIATION_AWAY":"MIL","NICKNAME_AWAY":"Bucks","WINNER":"MIL Bucks"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"NYK","NICKNAME_HOME":"Knicks","ABBREVIATION_AWAY":"ORL","NICKNAME_AWAY":"Magic","WINNER":"NYK Knicks"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"TOR","NICKNAME_HOME":"Raptors","ABBREVIATION_AWAY":"IND","NICKNAME_AWAY":"Pacers","WINNER":"TOR Raptors"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"OKC","NICKNAME_HOME":"Thunder","ABBREVIATION_AWAY":"UTA","NICKNAME_AWAY":"Jazz","WINNER":"OKC Thunder"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"DAL","NICKNAME_HOME":"Mavericks","ABBREVIATION_AWAY":"MEM","NICKNAME_AWAY":"Grizzlies","WINNER":"DAL Mavericks"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"PHX","NICKNAME_HOME":"Suns","ABBREVIATION_AWAY":"SAS","NICKNAME_AWAY":"Spurs","WINNER":"PHX Suns"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"DEN","NICKNAME_HOME":"Nuggets","ABBREVIATION_AWAY":"GSW","NICKNAME_AWAY":"Warriors","WINNER":"GSW Warriors"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"SAC","NICKNAME_HOME":"Kings","ABBREVIATION_AWAY":"HOU","NICKNAME_AWAY":"Rockets","WINNER":"HOU Rockets"},
  {"GAME_DATE_EST":"2024-12-03","ABBREVIATION_HOME":"LAC","NICKNAME_HOME":"Clippers","ABBREVIATION_AWAY":"POR","NICKNAME_AWAY":"Trail Blazers","WINNER":"LAC Clippers"}
]

@app.get("/")
def index():
  return Titled(
    "NBA Pick'em",
    Div(
      P("Here are today's picks"),
      Grid(
        Div("Date", style="font-weight: bold;"),
        Div("Home Team", style="font-weight: bold;"),
        Div("Away Team", style="font-weight: bold;"),
        Div("Winner", style="font-weight: bold;"),
      ),
      *[
        Grid(
          Div(game["GAME_DATE_EST"]),
          Div(game["NICKNAME_HOME"]),
          Div(game["NICKNAME_AWAY"]),
          Div(game["WINNER"])
        )
        for game in GAMES
      ]
    )
  )
