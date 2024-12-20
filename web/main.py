from fasthtml import FastHTML
from fasthtml.common import *
from services import assemble_todays_predictions, get_historical_accuracy


app = FastHTML(hdrs=picolink)


@app.get("/")
def index():
    historical_accuracy = _retrieve_historical_accuracy()
    todays_games = assemble_todays_predictions()
    if not todays_games:
        return Titled(
            "NBA Pick'em",
            historical_accuracy,
            Div(
                P("No games computed yet. Check back in a few minutes.")
            )
        )

    return Titled(
        "NBA Pick'em",
        historical_accuracy,
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

def _retrieve_historical_accuracy():
    accuracy = get_historical_accuracy()
    return Article(
        H1("Pick Performance in 2024"),
        P(f"Total Games: {accuracy["total_games"]}"),
        P(f"Correct Predictions: {accuracy["correct_predictions"]}"),
        P(f"% Correct: {accuracy["correct_predictions"] / accuracy["total_games"]}"),
    )
    

def _retrieve_game_predictions(game_date):
    pass
