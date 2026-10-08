#!/bin/sh
# Container entrypoint: migrate, load first-start data (DEMO_MODE only),
# then serve on the platform's PORT.
set -e
alembic -c database/migrations/alembic.ini upgrade head
python scripts/bootstrap_demo.py || echo "bootstrap failed; serving anyway"
exec uvicorn apps.backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
