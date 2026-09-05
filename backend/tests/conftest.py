"""Environment for the whole suite.

Only this: the settings object validates its inputs, so the variables have to
exist before anything reads them. Everything that needs a database, a storage
root or an HTTP client lives in tests/integration/conftest.py — the unit tests
under tests/unit need none of it and never start a container.
"""

import os

os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("PGPORT", "5433")
os.environ.setdefault("POSTGRES_DB", "backend_test")
os.environ.setdefault("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
