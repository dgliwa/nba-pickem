import os
from celery import Celery
from celery.utils.log import get_task_logger
from celery.schedules import crontab



app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL"))
logger = get_task_logger(__name__)

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):

    # test - executes every minute.
    # TODO: Replace with tasks that A) fetch today's games from API and predict results and B) save yesterday's results to database
    sender.add_periodic_task(
        crontab(minute='*'),
        add.delay(5, 5),
    )

@app.task
def add(x, y):
    logger.info(f'Adding {x} + {y}')
    return x * y
