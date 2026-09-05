"""Test harness for the file exchange service.

Everything here needs a running Postgres. Storage and the queue are injected
through dependency overrides rather than monkey-patched into module globals,
which is the practical payoff of the layering.
"""

import os

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from src.api.deps import get_storage
from src.app import app
from src.core.config import get_settings
from src.core.db import dispose_engine, get_engine
from src.domain.models import Base
from src.storage.local import LocalFileStorage
from src.workers import tasks as tasks_module

TEST_DB = os.environ["POSTGRES_DB"]

MAINTENANCE_DSN = (
    f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ['PGPORT']}/postgres"
)

TASK_NAMES = ("process_file",)


@pytest.fixture(scope="session", autouse=True)
async def _database() -> None:
    """Recreate the test database once per session and build the schema."""
    connection = await asyncpg.connect(MAINTENANCE_DSN)
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await connection.close()

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await dispose_engine()


@pytest.fixture(autouse=True)
async def _clean_tables() -> None:
    """Every test starts from empty tables."""
    async with get_engine().begin() as conn:
        await conn.execute(text("TRUNCATE alerts, files RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture(autouse=True)
def storage_dir(tmp_path):
    """Point the service at a temporary storage root, through DI."""
    directory = tmp_path / "files"
    directory.mkdir()

    app.dependency_overrides[get_storage] = lambda: LocalFileStorage(directory)
    yield directory
    app.dependency_overrides.pop(get_storage, None)


@pytest.fixture(autouse=True)
def enqueued(monkeypatch, storage_dir) -> list[tuple[str, tuple]]:
    """Record Celery publications instead of reaching for a broker.

    Returns ``(task_name, args)`` in publication order, so tests assert *that*
    work was scheduled without asserting *how* it is chained.
    """
    calls: list[tuple[str, tuple]] = []

    for name in TASK_NAMES:
        task = getattr(tasks_module, name)
        monkeypatch.setattr(
            task,
            "delay",
            lambda *args, _name=name: calls.append((_name, args)),
        )

    # The worker builds its own service, so it has to be given the same
    # storage root the API was overridden with.
    monkeypatch.setattr(get_settings(), "storage_dir", storage_dir)
    return calls


@pytest.fixture
def run_pipeline(enqueued):
    """Drain the recorded queue, executing whatever was published.

    Tests publish work through the API and then run the queue to exhaustion,
    so none of them has to know how many tasks the pipeline is made of.
    """

    cursor = 0

    async def _run() -> None:
        nonlocal cursor
        while cursor < len(enqueued):
            name, args = enqueued[cursor]
            cursor += 1
            await getattr(tasks_module, f"_{name}")(*args)

    return _run


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def uploaded(client) -> dict:
    """A single uploaded file, straight from the public API."""
    response = await client.post(
        "/files",
        data={"title": "Договор с подрядчиком"},
        files={"file": ("contract.txt", b"line one\nline two\n", "text/plain")},
    )
    assert response.status_code == 201
    return response.json()
