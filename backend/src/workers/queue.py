"""The Celery-backed implementation of the service's queue interface.

Kept apart from the service so the business logic never imports Celery, and
apart from the task module so importing the publisher does not drag in the
worker's engine.
"""


class CeleryProcessingQueue:
    def publish(self, file_id: str, metrics: dict) -> None:
        from src.workers.tasks import process_file

        process_file.delay(file_id, metrics)
