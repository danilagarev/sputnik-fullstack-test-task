"""Request-size guard.

Written against ASGI rather than ``BaseHTTPMiddleware``: the latter runs the
endpoint in a separate task and pumps the response through a memory stream, so
every chunk of a gigabyte download would cross a queue between two tasks. A
plain ASGI callable adds nothing to the path the bytes take.
"""

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.status import HTTP_413_CONTENT_TOO_LARGE
from starlette.types import ASGIApp, Receive, Scope, Send

from src.core.config import Settings


class MaxBodySizeMiddleware:
    """Refuse a too-large upload before anything reads it.

    Starlette's multipart parser spools each part to a temporary file before
    the handler runs, so the storage layer's own byte counter can only fire
    once the payload is already on disk. Checking the declared length first
    keeps an oversized request from being written at all.

    A request that arrives chunked declares no length and is caught further in,
    by that counter — which is why both checks exist.
    """

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self._app = app
        # The settings object, not the number: the limit is configuration, and
        # reading it per request keeps this and the storage layer on one value.
        self._settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._exceeds_limit(Headers(scope=scope)):
            response = JSONResponse(
                status_code=HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "File is too large"},
            )
            await response(scope, receive, send)
            return

        await self._app(scope, receive, send)

    def _exceeds_limit(self, headers: Headers) -> bool:
        declared = headers.get("content-length")
        return (
            declared is not None
            and declared.isdigit()
            and int(declared) > self._settings.max_upload_bytes
        )
