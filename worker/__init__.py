from twisted.internet import asyncioreactor
from worker.game_collector import collect_game_data
from worker.game_predictor import predict_todays_games

asyncioreactor.install()

__all__ = ["collect_game_data", "predict_todays_games"]
