.PHONY: up down build logs backend-shell db-shell migrate seed demo-data test test-backend test-frontend lint worker worker-logs sweep preflight smoke-provider

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

backend-shell:
	docker compose exec backend bash

db-shell:
	docker compose exec postgres psql -U $${POSTGRES_USER:-workwell} -d $${POSTGRES_DB:-workwell}

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python database/seeds/seed_demo.py

demo-data:
	docker compose exec backend python scripts/generate_demo_data.py

test-backend:
	pip install -q -r apps/backend/requirements.txt
	pytest tests -v

test-frontend:
	cd apps/frontend && npm install && npm run test --if-present

lint:
	ruff check .

# Run the worker in the foreground, outside Docker, against the local stack.
worker:
	.venv/bin/python -m apps.worker

worker-logs:
	docker compose logs -f worker

# Enqueue the daily sweep now rather than waiting for its scheduled hour.
sweep:
	.venv/bin/python scripts/run_sweep.py

# Validate the deployment config without a Docker daemon: compose syntax,
# every COPY source, and the env vars the compose files require.
preflight:
	.venv/bin/python scripts/preflight.py

# Smoke-test the configured model provider with a real key. This is the one
# path automated tests cannot cover.
smoke-provider:
	.venv/bin/python scripts/smoke_provider.py
