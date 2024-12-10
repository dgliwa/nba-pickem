import os
from celery import Celery
from celery.utils.log import get_task_logger
from celery.schedules import crontab

from . import game_collector

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    pass
    # test - executes every minute.
    # TODO: Replace with tasks that A) fetch today's games from API and predict results and B) save yesterday's results to database
    sender.add_periodic_task(
        crontab(minute='*/15'),
        collect_game_data.s(),
    )

@app.task
def collect_game_data() -> None:
    game_collector.collect_game_data()
