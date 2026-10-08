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
# The worker runs from this same image with a different command. Leaving it
# out would build an image whose `python -m apps.worker` exits immediately -
# and nothing in a single-container test would notice.
COPY apps/worker apps/worker

# The containers run with a read-only root filesystem, so compile once here
# rather than having every import fail to write its cache at runtime.
RUN python -m compileall -q /app

# Run as a non-root user (Phase 20): a container escape should not land on
# root, and nothing here needs write access to the image.
RUN useradd --create-home --uid 10001 workwell \
    && chown -R workwell:workwell /app
USER workwell

EXPOSE 8000

# Migrate, load first-start data when DEMO_MODE is on, then listen on $PORT
# (default 8000) on all interfaces.
CMD ["sh", "scripts/start_backend.sh"]
