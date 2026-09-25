.PHONY: up down build logs backend-shell db-shell migrate seed demo-data test test-backend test-frontend lint worker worker-logs sweep preflight smoke-provider ingest-knowledge agent-selftest backup backup-verify

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

# Re-embed the knowledge base. Required after any change of provider or
# embedding model - vectors from two models are not comparable, and the
# mismatch returns wrong guidance rather than an error.
ingest-knowledge:
	.venv/bin/python scripts/ingest_knowledge.py

# Run on each OS before a rollout: the collectors fail silently per
# platform, and a signal that is always zero gets learned as normal.
agent-selftest:
	.venv/bin/python apps/desktop-agent/selftest.py

backup:
	./scripts/backup.sh dump

# The half that matters. A backup nobody has restored is a file.
backup-verify:
	./scripts/backup.sh verify $$(ls -t backups/*.sql.gz | head -1)
