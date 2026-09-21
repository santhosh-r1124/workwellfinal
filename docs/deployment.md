# Deployment (Phase 21)

## What is actually verified

The production compose file, Dockerfiles and nginx config in this repo are
written but **have not been run end to end** — they were authored in an
environment without a Docker daemon. Treat the first deploy as a smoke test,
not a formality. The backend's Python imports, migrations, test suite and the
frontend production build are all verified; the container orchestration around
them is not.

## Single host

```bash
cp .env.example .env
# set at minimum: APP_SECRET_KEY, GEMINI_API_KEY, POSTGRES_PASSWORD,
# CORS_ORIGINS, VITE_API_BASE_URL
docker compose -f docker-compose.prod.yml up --build -d
```

The prod compose file uses `${VAR:?required}` for every secret, so it fails
fast with a named variable rather than silently starting with a dev default.

Then seed and ingest the knowledge base:

```bash
docker compose -f docker-compose.prod.yml exec backend python database/seeds/seed_demo.py
docker compose -f docker-compose.prod.yml exec backend python -c "
from apps.backend.core.database import SessionLocal
from rag.ingestion.pipeline import ingest_knowledge_base
db = SessionLocal(); print(ingest_knowledge_base(db)); db.close()"
```

Skip `scripts/generate_demo_data.py` in production — it writes synthetic
telemetry against real user rows.

## TLS

The `proxy` service is the only one published to the host. Put certificates at
`./docker/tls/fullchain.pem` and `./docker/tls/privkey.pem`. With certbot:

```bash
certbot certonly --standalone -d workwell.example.com
cp /etc/letsencrypt/live/workwell.example.com/{fullchain,privkey}.pem ./docker/tls/
```

## Secrets

`.env` files are adequate for a single host but are not a secret manager: they
sit on disk unencrypted and are readable by anyone with host access. For
anything beyond a pilot, source `APP_SECRET_KEY` and `GEMINI_API_KEY` from AWS
Secrets Manager, GCP Secret Manager or Vault and inject them at container
start. Rotating `APP_SECRET_KEY` invalidates every issued JWT (all users must
log in again) and invalidates the desktop agent's shared device token, so
rotate it during a maintenance window and redistribute agent config.

## Scaling beyond one host

The backend is stateless apart from Postgres and Redis, so it scales
horizontally as-is:

- Run Postgres as a managed service (RDS/Cloud SQL) with pgvector enabled.
  Confirm the provider's pgvector version supports the index type you want.
- Redis must be shared, not per-replica — rate limiting is a shared counter
  and degrades to per-replica budgets otherwise.
- Run `alembic upgrade head` as a one-off job **before** rolling new replicas,
  rather than from each container's start command as the single-host setup
  does. Concurrent migrations from N replicas will race.
- Agent orchestration runs inline in the request path. Under real load, move
  `run_orchestration` to a worker queue (Celery/RQ/Arq) and have the chat
  endpoint read the latest completed run. This is the main known scaling
  limitation of the current design.

## Observability

`/metrics` is Prometheus-format and is deliberately **blocked at the public
proxy**. Scrape it from inside the network:

```yaml
scrape_configs:
  - job_name: workwell-backend
    static_configs:
      - targets: ["backend:8000"]
```

Useful alerts: `workwell_llm_call_failures_total` rising (provider outage or
bad key), p95 of `workwell_http_request_duration_seconds` on the chat route,
and `workwell_safety_events_total{severity="crisis"}` — the last one should
page a human, since the product's safety policy assumes escalation reaches
someone.

Logs are JSON on stdout with a `request_id` per request; the same id is
returned in the `X-Request-ID` response header, so a user-reported problem can
be traced to its log line.

## Backups

Postgres holds everything that matters. `pg_dump` nightly and verify a restore
periodically. Note that the retention policy (Admin → retention) deletes
telemetry past its window; if a backup is restored from before a retention
run, that data returns, which may conflict with what employees were told about
retention. Prune backups on the same schedule as the retention window.

## Pre-flight checklist

- [ ] `APP_ENV=production` (`/health` reports AI as configured; startup fails
      without `GEMINI_API_KEY`)
- [ ] `APP_SECRET_KEY` is a fresh random value, not the dev default
- [ ] `CORS_ORIGINS` lists only the real frontend origin
- [ ] TLS certificates present and auto-renewing
- [ ] Postgres port not published to the host
- [ ] A restore from backup has been tested at least once
- [ ] Gemini connectivity smoke-tested with the production key
