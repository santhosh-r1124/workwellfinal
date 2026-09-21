.PHONY: up down build logs backend-shell db-shell migrate seed demo-data test test-backend test-frontend lint

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
