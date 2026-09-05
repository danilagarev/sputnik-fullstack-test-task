"""Application assembly: lifespan, middleware, routers, error handlers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.errors import domain_error_handler
from src.api.middleware import MaxBodySizeMiddleware
from src.api.routers import alerts, files
from src.core.config import get_settings
from src.core.db import dispose_engine
from src.core.exceptions import DomainError
from src.storage.local import LocalFileStorage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Side effects that used to happen on import now happen on startup."""
    settings = get_settings()
    LocalFileStorage(settings.storage_dir).ensure_ready()
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="File exchange", lifespan=lifespan)

    # An upload is refused here, on the declared length, before the multipart
    # parser spools it to a temporary file; what arrives without a length is
    # caught by the storage layer's byte counter instead.
    app.add_middleware(MaxBodySizeMiddleware, settings=settings)

    app.add_middleware(
        CORSMiddleware,
        # Configuration rather than a constant: the allowed origins differ per
        # deployment, and localhost was hardcoded here.
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(DomainError, domain_error_handler)

    app.include_router(files.router)
    app.include_router(alerts.router)
    return app


app = create_app()
