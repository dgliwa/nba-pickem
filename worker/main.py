import os
from celery import Celery
from celery.utils.log import get_task_logger
from celery.schedules import crontab

from worker.game_collector import collect_game_data

app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute='0'),
        collect_game_data.s(),
    )
