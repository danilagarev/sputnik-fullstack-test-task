"""Celery configuration only — no tasks, no engine, no business logic."""

from celery import Celery

from src.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "file_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
    include=["src.workers.tasks"],
)

celery_app.conf.update(
    # A task is acknowledged after it has run, so a worker lost mid-flight does
    # not lose the file. Redelivery is safe because processing claims its row.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
