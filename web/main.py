from fasthtml import FastHTML
from fasthtml.common import *
from services import assemble_todays_predictions


app = FastHTML(hdrs=picolink)


@app.get("/")
def index():
    todays_games = assemble_todays_predictions()
    if not todays_games:
        return Titled("NBA Pick'em", P("No games computed yet. Check back in a few minutes."))

    return Titled("NBA Pick'em",
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
                for game in todays_games
            ]
        )
    )
