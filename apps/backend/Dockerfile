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
COPY shared shared
COPY database database
COPY scripts scripts
COPY apps/backend apps/backend

EXPOSE 8000

CMD ["sh", "-c", "alembic -c database/migrations/alembic.ini upgrade head && uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000"]
