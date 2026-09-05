FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local
WORKDIR /backend

COPY pyproject.toml uv.lock ./
# Pinned for the same reason postgres is: an unpinned tag makes the build's
# behaviour change under the project without a line changing in this file.
COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /uvx /bin/
RUN uv sync --locked

COPY src ./src
# Migrations belong in the image: `alembic upgrade head` has to work in a
# container that has no bind mount from the host.
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

# Nothing here needs root, and the API is the process most exposed to input it
# did not choose. The storage root is created and handed over now: a named
# volume mounted over it inherits this ownership, which is what lets an
# unprivileged process write uploads into it.
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid 1001 --create-home app \
    && mkdir -p /backend/storage/files \
    && chown -R app:app /backend
USER app
