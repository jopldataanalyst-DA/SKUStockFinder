import logging

from apscheduler.schedulers.background import BackgroundScheduler

from . import db, unicommerce
from .config import settings

logger = logging.getLogger("skufinder.scheduler")

scheduler = BackgroundScheduler()


def run_fetch_job() -> int:
    rows = unicommerce.fetch_all_facilities()
    return db.upsert_rows(rows)


def start_scheduler() -> None:
    scheduler.add_job(
        run_fetch_job,
        "interval",
        minutes=settings.fetch_interval_minutes,
        id="unicommerce_fetch",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: fetching every %d minutes", settings.fetch_interval_minutes)
