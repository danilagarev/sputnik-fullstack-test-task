"""Engine and session lifecycle.

There used to be two engines — one in the web module, one in the worker — each
created as an import side effect, with the worker importing its URL from the
web layer. Both are built here instead, lazily, so importing the package
neither opens a pool nor requires the environment to be populated.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """One session per unit of work, closed whatever happens inside it."""
    async with get_session_factory()() as session:
        yield session


async def dispose_engine() -> None:
    """Release the pool. Called from the app lifespan and by the worker."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
