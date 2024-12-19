from twisted.internet import asyncioreactor
from worker.game_collector import collect_game_data

asyncioreactor.install()

__all__ = ["collect_game_data"]
