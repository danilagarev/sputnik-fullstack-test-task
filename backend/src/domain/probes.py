"""The content probe interface.

Both sides of the single-pass upload depend on it: ``services.scanning``
implements it and ``storage`` feeds it, so it belongs to neither.
"""

from typing import Protocol


class ContentProbe(Protocol):
    """Accumulates a metric from a stream of chunks."""

    def feed(self, chunk: bytes) -> None: ...

    def result(self) -> dict[str, int]: ...
