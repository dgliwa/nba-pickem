import json
from fasthtml import FastHTML
from fasthtml.common import Div, P, picolink, Titled, Grid, Article, H1, Button, Link, Details, Summary, Span, Card, Article, Code
from services import predictions_for_date, get_historical_accuracy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


colors = Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.colors.min.css")
app = FastHTML(hdrs=[picolink, colors])


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
    bet_amount = 10.0
    predictions = predictions_for_date(game_date, bet_amount)

    if not predictions:
        return Div(
            P(f"No predictions for {game_date.strftime('%Y-%m-%d')}"),
            _buttons(game_date),
            id="picks"
        )

    return Div(
        Div(
            P(f"Here are the picks for {game_date.strftime('%Y-%m-%d')}"),
            P(f"All winnings calculated on a {bet_amount} bet"),
            Grid(
                Div("Date", style="font-weight: bold;"),
                Div("Home Team", style="font-weight: bold;"),
                Div("Away Team", style="font-weight: bold;"),
                Div("Predicted Winner", style="font-weight: bold;"),
                Div("Actual Winner", style="font-weight: bold;"),
            ),
            *[
                _game(game)
                for game in predictions
            ],
        ),
        _buttons(game_date),
        id="picks"
    )


def _game(game):
    prediction_keys = [
        "HOME_WIN_PCT",
        "HOME_HOME_WIN_PCT",
        "AWAY_WIN_PCT",
        "AWAY_AWAY_WIN_PCT",
        "HOME_TEAM_B2B",
        "AWAY_TEAM_B2B",
        "HOME_LAST_10_WIN_PCT",
        "AWAY_LAST_10_WIN_PCT",
    ]
    if game["ACTUAL_WINNER"]:
        return Card(
            Details(
                Summary(
                    Grid(
                        Div(game["GAME_DATE_EST"]),
                        Div(f"{game['NICKNAME_HOME']} ({game['HOME_ODDS']})"),
                        Div(f"{game['NICKNAME_AWAY']} ({game['AWAY_ODDS']})"),
                        Div(game["PREDICTED_WINNER"]),
                        Div(game["ACTUAL_WINNER"]),
                    ),
                    Grid(
                        Div(Span(f"Winnings: {game['GAME_WINNINGS']}")),
                    ),
                ),
                Card(
                    Code(
                        json.dumps({ k: game[k] for k in prediction_keys })
                    )
                )
            ),
            
            cls=_bg_class(game)
        )
    else:
        return Card(
            Details(
                Summary(
                    Grid(
                        Div(game["GAME_DATE_EST"]),
                        Div(game["NICKNAME_HOME"]),
                        Div(game["NICKNAME_AWAY"]),
                        Div(game["PREDICTED_WINNER"]),
                        Div(game["ACTUAL_WINNER"]),
                    )
                ),
                Card(
                    Code(
                        json.dumps({ k: game[k] for k in prediction_keys })
                    )
                )
            )
        )


def _bg_class(game):
    if game["WIN_AGAINST_MONEYLINE"]:
        return "pico-background-yellow-100"
    if game["CORRECT_PREDICTION"]:
        return "pico-background-jade-500"
    elif game["CORRECT_PREDICTION"] is False:
        return "pico-background-red-500"
    else:
        return None


def _retrieve_historical_accuracy():
    bet_amount = 10.0
    accuracy = get_historical_accuracy(bet_amount)
    return Article(
        H1("Pick Performance in 2024"),
        P(f"Total Games: {accuracy['total_games']}"),
        P(f"Correct Predictions: {accuracy['correct_predictions']}"),
        P(f"% Correct: {accuracy['correct_predictions'] / accuracy['total_games']}"),
        P(f"Predicted winnings (assuming a ${bet_amount} bet): {accuracy['predicted_winnings']}"),
        P(f"Correct picks against the moneyline favorite: {accuracy['against_moneyline_favorite']}"),
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
