from fasthtml import FastHTML
from fasthtml.common import Div, P, picolink, Titled, Grid, Article, H1, Button
from services import predictions_for_date, get_historical_accuracy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


app = FastHTML(hdrs=picolink)


@app.get("/")
def index():
    game_date = datetime.now(ZoneInfo('US/Eastern')).date()
    return Titled(
        "NBA Pick'em",
        _retrieve_historical_accuracy(),
        _retrieve_game_predictions(game_date)
    )


@app.get("/previous_picks")
def _previous_picks(game_date: str):
    game_date_obj = datetime.strptime(game_date, "%Y-%m-%d").date()
    return _retrieve_game_predictions(game_date_obj)


def _retrieve_game_predictions(game_date):
    predictions = predictions_for_date(game_date)

    if not predictions:
        return Div(
            P(f"No predictions for {game_date.strftime("%Y-%m-%d")}"),
            _buttons(game_date),
            id="picks"
        )

    return Div(
        Div(
            P(f"Here are the picks for {game_date.strftime("%Y-%m-%d")}"),
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
                for game in predictions
            ],
        ),
        _buttons(game_date),
        id="picks"
    )


def _retrieve_historical_accuracy():
    accuracy = get_historical_accuracy()
    return Article(
        H1("Pick Performance in 2024"),
        P(f"Total Games: {accuracy["total_games"]}"),
        P(f"Correct Predictions: {accuracy["correct_predictions"]}"),
        P(f"% Correct: {accuracy["correct_predictions"] / accuracy["total_games"]}"),
    )


def _buttons(game_date):
    today = datetime.now(ZoneInfo('US/Eastern')).date()
    buttons = []
    yesterday = (game_date + timedelta(days=-1)).strftime("%Y-%m-%d")
    buttons.append(Button(yesterday, type="Button", hx_target="#picks", hx_get=f"/previous_picks?game_date={yesterday}"))
    if game_date != today:
        tomorrow = (game_date + timedelta(days=1)).strftime("%Y-%m-%d")
        buttons.append(Button(tomorrow, type="Button", hx_target="#picks", hx_get=f"/previous_picks?game_date={tomorrow}"))
    return Div(
        *[button for button in buttons]
    )
