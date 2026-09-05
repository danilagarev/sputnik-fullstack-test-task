"""All queries against the files table.

Keeping them out of the service is what lets the service be read — and tested —
without SQL in the way, and puts every access path for a table in one place.
"""

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import ProcessingStatus
from src.domain.models import StoredFile


class FileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, file_id: str) -> StoredFile | None:
        return await self._session.get(StoredFile, file_id)

    async def list(self, *, limit: int) -> Sequence[StoredFile]:
        statement = (
            select(StoredFile)
            .order_by(StoredFile.created_at.desc(), StoredFile.id.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def claim_for_processing(self, file_id: str) -> bool:
        """Move a row from ``uploaded`` to ``processing``, exactly once.

        A conditional update rather than a read followed by a write: the check
        and the transition are one statement, so a redelivered task cannot pass
        it twice and raise a second alert for one upload.
        """
        # `execute` is typed as returning a Result; an UPDATE always yields a
        # CursorResult, the only one that carries a row count.
        result = cast(
            "CursorResult[Any]",
            await self._session.execute(
                update(StoredFile)
                .where(
                    StoredFile.id == file_id,
                    StoredFile.processing_status == ProcessingStatus.UPLOADED,
                )
                .values(processing_status=ProcessingStatus.PROCESSING)
            ),
        )
        await self._session.commit()
        return result.rowcount == 1

    def add(self, file_item: StoredFile) -> None:
        self._session.add(file_item)

    async def delete(self, file_item: StoredFile) -> None:
        await self._session.delete(file_item)
