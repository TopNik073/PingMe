FROM python:3.12-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app_dir/src
RUN apt-get update && \
    apt-get install --yes --no-install-recommends netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app_dir

FROM base AS builder

RUN pip install --upgrade "uv>=0.6,<1.0" && rm -rf /root/.cache/*
ADD pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --verbose --no-progress

FROM base AS final

RUN pip install --upgrade "uv>=0.6,<1.0"
COPY --from=builder /app_dir/.venv ./.venv
COPY src/ ./src
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Run migrations and start the application
CMD while ! nc -z db 5432; do sleep 0.1; done && \
    ./.venv/bin/alembic upgrade head && \
    ./.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 