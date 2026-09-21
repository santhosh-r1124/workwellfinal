FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/backend/requirements.txt apps/backend/requirements.txt
RUN pip install -r apps/backend/requirements.txt

COPY agents agents
COPY ml ml
COPY rag rag
COPY safety safety
COPY integrations integrations
COPY shared shared
COPY database database
COPY scripts scripts
COPY apps/backend apps/backend

# Run as a non-root user (Phase 20): a container escape should not land on
# root, and nothing here needs write access to the image.
RUN useradd --create-home --uid 10001 workwell \
    && chown -R workwell:workwell /app
USER workwell

EXPOSE 8000

CMD ["sh", "-c", "alembic -c database/migrations/alembic.ini upgrade head && uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000"]
