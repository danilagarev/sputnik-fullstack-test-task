"""Business logic for stored files.

Knows nothing about FastAPI and nothing about Celery: it raises domain errors
and publishes through a queue interface. That is what lets the same code serve
an HTTP request and a background worker without either importing the other.
"""

import logging
import mimetypes
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.exceptions import (
    EmptyUpload,
    FieldRequired,
    FieldTooLong,
    FileNotFound,
    StoredPayloadMissing,
)
from src.domain.enums import AlertLevel, ProcessingStatus, ScanStatus
from src.domain.models import Alert, StoredFile
from src.repositories.alerts import AlertRepository
from src.repositories.files import FileRepository
from src.services import scanning
from src.storage.local import LocalFileStorage, storage_suffix

logger = logging.getLogger(__name__)

DETAILS_LIMIT = 500
# Both columns are String(255); unchecked input reached the database and came
# back as an integrity error, i.e. a 500 for what is a client mistake.
NAME_LIMIT = 255
PAYLOAD_MISSING = "stored file not found during metadata extraction"


def _clean_title(title: str) -> str:
    """The one rule both write paths share, applied the same way by both.

    A blank title used to be accepted by POST and PATCH alike: the browser
    trimmed its input, so the interface never produced one, and any other
    client could rename a file to nothing.
    """
    title = title.strip()
    if not title:
        raise FieldRequired("title")
    if len(title) > NAME_LIMIT:
        raise FieldTooLong("title", NAME_LIMIT)
    return title


class ProcessingQueue(Protocol):
    """Whatever carries a file into background processing."""

    def publish(self, file_id: str, metrics: dict) -> None: ...


class FileService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        files: FileRepository,
        alerts: AlertRepository,
        storage: LocalFileStorage,
        queue: ProcessingQueue,
        settings: Settings,
    ) -> None:
        self._session = session
        self._files = files
        self._alerts = alerts
        self._storage = storage
        self._queue = queue
        self._settings = settings

    async def list_files(self, *, limit: int) -> Sequence[StoredFile]:
        return await self._files.list(limit=limit)

    async def list_alerts(self, *, limit: int) -> Sequence[Alert]:
        return await self._alerts.list(limit=limit)

    async def get_file(self, file_id: str) -> StoredFile:
        file_item = await self._files.get(file_id)
        if file_item is None:
            raise FileNotFound(file_id)
        return file_item

    async def create_file(
        self,
        *,
        title: str,
        filename: str | None,
        content_type: str | None,
        chunks: AsyncIterator[bytes],
    ) -> StoredFile:
        """Store an upload and schedule its processing.

        The payload is walked exactly once: the same pass that writes it to
        disk also measures it, so the worker never has to read it back. The
        metrics travel to the worker in the task payload.
        """
        title = _clean_title(title)
        if filename is not None and len(filename) > NAME_LIMIT:
            raise FieldTooLong("filename", NAME_LIMIT)

        file_id = str(uuid4())
        stored_name = f"{file_id}{storage_suffix(filename)}"
        mime_type = (
            content_type or mimetypes.guess_type(stored_name)[0] or "application/octet-stream"
        )

        probes = scanning.probes_for(mime_type)
        size = await self._storage.save(
            stored_name,
            chunks,
            max_bytes=self._settings.max_upload_bytes,
            probes=probes,
        )
        if size == 0:
            self._storage.delete(stored_name)
            raise EmptyUpload

        file_item = StoredFile(
            id=file_id,
            title=title,
            original_name=filename or stored_name,
            stored_name=stored_name,
            mime_type=mime_type,
            size=size,
            processing_status=ProcessingStatus.UPLOADED,
        )

        self._files.add(file_item)
        try:
            await self._session.commit()
        except BaseException:
            # Never leave bytes on disk that no row points at.
            self._storage.delete(stored_name)
            raise

        try:
            self._queue.publish(file_id, scanning.collect(probes))
        except Exception:
            # The bytes are on disk and the row is committed, so the upload did
            # succeed; failing the request would be a lie. The row stays in
            # `uploaded` and this record is what a sweeper would key off.
            logger.exception("failed to publish processing", extra={"file_id": file_id})

        return file_item

    async def update_file(self, file_id: str, *, title: str) -> StoredFile:
        title = _clean_title(title)
        file_item = await self.get_file(file_id)
        file_item.title = title
        await self._session.commit()
        return file_item

    async def delete_file(self, file_id: str) -> None:
        file_item = await self.get_file(file_id)
        stored_name = file_item.stored_name

        await self._files.delete(file_item)
        # Commit first: the row and its alerts go together, and the bytes are
        # only discarded once that has actually succeeded.
        await self._session.commit()
        self._storage.delete(stored_name)

    async def open_for_download(self, file_id: str) -> tuple[StoredFile, Path]:
        file_item = await self.get_file(file_id)
        if not self._storage.holds(file_item.stored_name):
            raise StoredPayloadMissing(file_item.stored_name)
        return file_item, self._storage.path(file_item.stored_name)

    async def process_file(self, file_id: str, metrics: dict | None = None) -> None:
        """Scan, describe and announce a file — the whole background pipeline.

        This was three Celery tasks, each re-fetching the same row in its own
        session and transaction. The steps are strictly sequential, share all
        their inputs, and none had its own retry policy, so the split cost
        three broker round trips and three transactions and bought nothing.
        """
        # Claiming the row is one statement and fails for a row that is already
        # claimed, already finished or gone: `task_acks_late` may redeliver a
        # task that in fact completed, and re-running it would raise a second
        # alert for a single upload.
        if not await self._files.claim_for_processing(file_id):
            return

        file_item = await self._files.get(file_id)
        if file_item is None:  # pragma: no cover - deleted between two statements
            return

        try:
            verdict = scanning.scan(
                original_name=file_item.original_name,
                size=file_item.size,
                mime_type=file_item.mime_type,
            )
            file_item.scan_status = verdict.status
            file_item.scan_details = verdict.details
            file_item.requires_attention = verdict.requires_attention

            if not self._storage.holds(file_item.stored_name):
                raise StoredPayloadMissing(file_item.stored_name)

            file_item.metadata_json = scanning.describe(
                original_name=file_item.original_name,
                size=file_item.size,
                mime_type=file_item.mime_type,
                metrics=metrics or {},
            )
            file_item.processing_status = ProcessingStatus.PROCESSED
        except StoredPayloadMissing:
            self._mark_failed(file_item, PAYLOAD_MISSING)
        except Exception as error:
            # Any failure has to be terminal: a row left in `processing` is
            # invisible to the user and to every retry mechanism.
            self._mark_failed(file_item, f"processing failed: {error}")

        self._raise_alert(file_item)
        await self._session.commit()

    @staticmethod
    def _mark_failed(file_item: StoredFile, details: str) -> None:
        file_item.processing_status = ProcessingStatus.FAILED
        file_item.scan_status = file_item.scan_status or ScanStatus.FAILED
        file_item.scan_details = details[:DETAILS_LIMIT]

    def _raise_alert(self, file_item: StoredFile) -> None:
        if file_item.processing_status == ProcessingStatus.FAILED:
            level, message = AlertLevel.CRITICAL, "File processing failed"
        elif file_item.requires_attention:
            level = AlertLevel.WARNING
            message = f"File requires attention: {file_item.scan_details}"
        else:
            level, message = AlertLevel.INFO, "File processed successfully"

        self._alerts.add(file_id=file_item.id, level=level, message=message)
