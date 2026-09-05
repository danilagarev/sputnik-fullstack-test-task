"""Dependency providers.

The original code used no ``Depends`` at all: every function reached for a
global session factory, so transaction boundaries could not be controlled and
nothing could be substituted in a test.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.db import session_scope
from src.repositories.alerts import AlertRepository
from src.repositories.files import FileRepository
from src.services.files import FileService
from src.storage.local import LocalFileStorage
from src.workers.queue import CeleryProcessingQueue

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_scope() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_storage(settings: SettingsDep) -> LocalFileStorage:
    return LocalFileStorage(settings.storage_dir)


StorageDep = Annotated[LocalFileStorage, Depends(get_storage)]


def get_queue() -> CeleryProcessingQueue:
    return CeleryProcessingQueue()


QueueDep = Annotated[CeleryProcessingQueue, Depends(get_queue)]


def get_file_service(
    session: SessionDep,
    storage: StorageDep,
    queue: QueueDep,
    settings: SettingsDep,
) -> FileService:
    return FileService(
        session=session,
        files=FileRepository(session),
        alerts=AlertRepository(session),
        storage=storage,
        queue=queue,
        settings=settings,
    )


FileServiceDep = Annotated[FileService, Depends(get_file_service)]


def get_limit(
    settings: SettingsDep,
    limit: Annotated[int | None, Query(ge=1)] = None,
) -> int:
    """How many rows a list endpoint may return.

    Both lists used to return the whole table: one query whose cost grows with
    the data, on the page the user opens first.
    """
    return min(limit or settings.default_page_size, settings.max_page_size)


LimitDep = Annotated[int, Depends(get_limit)]
