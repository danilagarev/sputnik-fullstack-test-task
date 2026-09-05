"""Local filesystem storage.

Behind an interface narrow enough that swapping it for S3 is a matter of
writing a second implementation. Uploads are streamed: the previous code read
the whole request body into memory with a single ``await upload_file.read()``
before writing it out.
"""

import asyncio
import re
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import BinaryIO

from src.core.exceptions import UploadTooLarge
from src.domain.probes import ContentProbe

# The client's filename reaches a filesystem path and a String(255) column, so
# the suffix it contributes is bounded and limited to harmless characters.
SAFE_SUFFIX = re.compile(r"\.[A-Za-z0-9]{1,31}\Z")


def storage_suffix(filename: str | None) -> str:
    """The extension to give the stored copy, or none.

    Anything that does not look like an extension is dropped rather than
    refused: "Отчёт за 2026.09 итог" is an ordinary name. The stored name is a
    UUID and the original is kept on the row, so nothing is lost.
    """
    suffix = Path(filename or "").suffix
    return suffix if SAFE_SUFFIX.fullmatch(suffix) else ""


def _absorb(sink: BinaryIO, chunk: bytes, probes: Sequence[ContentProbe]) -> None:
    """Write one chunk and let every probe see it, in one hop off the loop."""
    sink.write(chunk)
    for probe in probes:
        probe.feed(chunk)


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def ensure_ready(self) -> None:
        """Create the storage root. Called from the lifespan, not on import."""
        self._root.mkdir(parents=True, exist_ok=True)

    def path(self, name: str) -> Path:
        return self._root / name

    def holds(self, name: str) -> bool:
        """True only for a readable regular file, not for a directory."""
        return self.path(name).is_file()

    def delete(self, name: str) -> None:
        self.path(name).unlink(missing_ok=True)

    async def save(
        self,
        name: str,
        chunks: AsyncIterator[bytes],
        *,
        max_bytes: int,
        probes: Sequence[ContentProbe] = (),
    ) -> int:
        """Write a stream to disk, measuring it on the way past.

        Returns the number of bytes written. Probes see every chunk, so the
        payload is walked once no matter how many metrics are wanted. A partial
        file is removed if the limit is hit or the write fails.
        """
        self.ensure_ready()
        destination = self.path(name)
        size = 0

        try:
            with destination.open("wb") as sink:
                async for chunk in chunks:
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > max_bytes:
                        raise UploadTooLarge(max_bytes)
                    # File I/O releases the GIL: on the event loop a large
                    # upload would stall every other request for its duration.
                    await asyncio.to_thread(_absorb, sink, chunk, probes)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise

        return size
