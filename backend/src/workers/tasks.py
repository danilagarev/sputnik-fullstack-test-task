"""Background processing: one task, one session, one pass.

What used to be three chained tasks — scan, extract metadata, alert — each
publishing the next and re-reading the same row in its own session.

The event loop is per worker process and created after the fork, not inherited:
an asyncpg pool belongs to the loop that first touched it, and a pool created
before ``fork()`` hands broken sockets to every child.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any

from celery.signals import worker_process_init, worker_process_shutdown

from src.core.config import get_settings
from src.core.db import dispose_engine, get_session_factory
from src.repositories.alerts import AlertRepository
from src.repositories.files import FileRepository
from src.services.files import FileService
from src.storage.local import LocalFileStorage
from src.workers.celery_app import celery_app
from src.workers.queue import CeleryProcessingQueue

_loop: asyncio.AbstractEventLoop | None = None


@worker_process_init.connect
def _open_loop(**_: object) -> None:
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)


@worker_process_shutdown.connect
def _close_loop(**_: object) -> None:
    global _loop
    if _loop is not None and not _loop.is_closed():
        _loop.run_until_complete(dispose_engine())
        _loop.close()
    _loop = None


def _run(coroutine: Coroutine[Any, Any, None]) -> None:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    _loop.run_until_complete(coroutine)


async def _process_file(file_id: str, metrics: dict | None = None) -> None:
    settings = get_settings()
    async with get_session_factory()() as session:
        service = FileService(
            session=session,
            files=FileRepository(session),
            alerts=AlertRepository(session),
            storage=LocalFileStorage(settings.storage_dir),
            queue=CeleryProcessingQueue(),
            settings=settings,
        )
        await service.process_file(file_id, metrics)


# No retry policy: the service turns every failure into a terminal state and an
# alert, so there is nothing for Celery to retry.
@celery_app.task(name="process_file")
def process_file(file_id: str, metrics: dict | None = None) -> None:
    _run(_process_file(file_id, metrics))
