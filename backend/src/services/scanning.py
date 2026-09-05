"""Scan rules and content metrics — pure, dependency-free, fast to test.

The verdict is a function of fields the row already holds, so it never touches
the disk. The probes consume the upload one chunk at a time, which is what lets
the payload be measured during the single pass that writes it.
"""

import codecs
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from src.domain.enums import ScanStatus
from src.domain.probes import ContentProbe

SUSPICIOUS_EXTENSIONS = frozenset({".exe", ".bat", ".cmd", ".sh", ".js"})
MAX_UNREMARKABLE_SIZE = 10 * 1024 * 1024
PDF_COMPATIBLE_MIME_TYPES = frozenset({"application/pdf", "application/octet-stream"})
NO_THREATS = "no threats found"


@dataclass(frozen=True)
class ScanVerdict:
    status: ScanStatus
    details: str
    requires_attention: bool


def scan(*, original_name: str, size: int, mime_type: str) -> ScanVerdict:
    """Classify a file from its metadata alone."""
    extension = Path(original_name).suffix.lower()
    reasons: list[str] = []

    if extension in SUSPICIOUS_EXTENSIONS:
        reasons.append(f"suspicious extension {extension}")

    if size > MAX_UNREMARKABLE_SIZE:
        reasons.append("file is larger than 10 MB")

    if extension == ".pdf" and mime_type not in PDF_COMPATIBLE_MIME_TYPES:
        reasons.append("pdf extension does not match mime type")

    if not reasons:
        return ScanVerdict(ScanStatus.CLEAN, NO_THREATS, requires_attention=False)

    return ScanVerdict(ScanStatus.SUSPICIOUS, ", ".join(reasons), requires_attention=True)


class TextProbe:
    """Counts lines and characters without holding the document in memory.

    Both counts are running integers, so the state stays constant however large
    the stream is. Decoding is incremental so multi-byte characters split
    across chunks are not mangled, and a trailing carriage return is held back
    in case the next chunk turns it into a CRLF pair.
    """

    # Everything str.splitlines() treats as a break, so the count matches it.
    BOUNDARIES = frozenset("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")

    def __init__(self) -> None:
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="ignore")
        self._characters = 0
        self._boundaries = 0
        self._unterminated = False
        self._pending_cr = False

    def feed(self, chunk: bytes) -> None:
        self._consume(self._decoder.decode(chunk))

    def _consume(self, text: str) -> None:
        self._characters += len(text)
        if not text:
            return

        if self._pending_cr:
            # The held "\r" ends a line on its own, and swallows a leading
            # "\n" as the other half of a CRLF pair.
            self._pending_cr = False
            self._boundaries += 1
            self._unterminated = False
            if text[0] == "\n":
                text = text[1:]
                if not text:
                    return

        if text[-1] == "\r":
            self._pending_cr = True
            text = text[:-1]
            if not text:
                return

        parts = text.splitlines(keepends=True)
        if text[-1] in self.BOUNDARIES:
            self._boundaries += len(parts)
            self._unterminated = False
        else:
            self._boundaries += len(parts) - 1
            self._unterminated = True

    def result(self) -> dict[str, int]:
        self._consume(self._decoder.decode(b"", final=True))
        if self._pending_cr:
            self._pending_cr = False
            self._boundaries += 1
            self._unterminated = False
        lines = self._boundaries + (1 if self._unterminated else 0)
        return {"line_count": lines, "char_count": self._characters}


class PdfPageProbe:
    """Counts page objects across chunk boundaries.

    The original searched for ``/Type /Page`` with a space, which producers do
    not emit, so every document was reported as one page. ``/Type/Pages`` is the
    page tree and must not be counted.
    """

    PATTERN = re.compile(rb"/Type\s*/Page(?![sA-Za-z])")
    OVERLAP = 64

    def __init__(self) -> None:
        self._count = 0
        self._pending = b""

    def feed(self, chunk: bytes) -> None:
        buffer = self._pending + chunk
        cutoff = max(len(buffer) - self.OVERLAP, 0)
        self._count += sum(1 for match in self.PATTERN.finditer(buffer) if match.start() < cutoff)
        self._pending = buffer[cutoff:]

    def result(self) -> dict[str, int]:
        self._count += sum(1 for _ in self.PATTERN.finditer(self._pending))
        self._pending = b""
        return {"approx_page_count": max(self._count, 1)}


def probes_for(mime_type: str) -> list[ContentProbe]:
    """Pick the metrics worth collecting for a content type."""
    if mime_type.startswith("text/"):
        return [TextProbe()]
    if mime_type == "application/pdf":
        return [PdfPageProbe()]
    return []


def collect(probes: Iterable[ContentProbe]) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for probe in probes:
        metrics.update(probe.result())
    return metrics


def describe(*, original_name: str, size: int, mime_type: str, metrics: dict) -> dict:
    """Assemble the metadata document stored on the row."""
    return {
        "extension": Path(original_name).suffix.lower(),
        "size_bytes": size,
        "mime_type": mime_type,
        **metrics,
    }
