# Deployment (Phase 21)

## What is actually verified

The production compose file, Dockerfiles and nginx config in this repo are
written but **have not been run end to end** — they were authored in an
environment without a Docker daemon. Treat the first deploy as a smoke test,
not a formality.

What *is* verified: the backend's Python imports, the migrations (applied
against a real Postgres, and checked against the models by
`scripts/check_migrations.py`), the full test suite against real Postgres and
Redis, the worker running its own jobs end to end, and the frontend production
build.

Two checks stand in for the build nobody could run here:

```bash
make preflight        # every COPY source, every module a container runs,
                      # every bind mount, every required env var
make smoke-provider   # the real model provider, with the real key
```

`preflight` exists because of specific bugs: the backend image was missing
`COPY safety` for weeks, and later `COPY apps/worker`. Both would have built
cleanly and died on first import. It now catches that class statically,
including transitively — a package the copied code imports must itself be
copied.

`smoke-provider` covers the one path automated tests cannot: the suite runs
against the deterministic local provider, and the graceful-degradation work
means a misconfigured key no longer crashes anything — it just makes every
explanation quietly fall back to canned text. Run it with the production key
before you believe the narration works.

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
start. Rotating `APP_SECRET_KEY` invalidates every issued JWT (all users must log
in again), so rotate it during a maintenance window. It no longer affects
desktop agents: those hold per-device tokens, which are independent of it
and revoked individually.

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
- Run one `worker` container. More than one is safe — the scheduler lock and
  the queue's dedupe keys make the daily sweep single-winner — but at this job
  volume (one analysis per employee per day) one is plenty. What is *not* safe
  is zero: without a worker nothing is analysed on a schedule, and
  `/health/ready` reports `worker: absent` precisely so that is visible.

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
- [ ] `make preflight` passes against the real `.env`
- [ ] `make smoke-provider` passes with the production key
- [ ] A `worker` container is running (`/health/ready` reports
      `worker: running`)
- [ ] `NOTIFICATION_CHANNEL` and `APP_BASE_URL` set deliberately
- [ ] `INLINE_ANALYSIS_FALLBACK=false` (a worker is deployed, so the API must
      never run an analysis on a request)

## The background worker

The worker is what makes this an early-warning system rather than an on-demand
report. Without it, `run_orchestration` is reachable only from the chat
endpoint — so the employee who never opens a wellbeing dashboard, the one the
product exists for, is never analysed at all.

```bash
docker compose -f docker-compose.prod.yml up -d worker
docker compose -f docker-compose.prod.yml logs -f worker
```

It runs two things on a timer:

- **The daily sweep**, at `DAILY_ANALYSIS_HOUR_UTC` (default 02:00), which
  enqueues one analysis per active employee. Jobs return before any model call
  for employees without consent or without enough history, so the sweep does
  not need to know who is eligible — and cannot drift from the rule that
  decides.
- **Retention**, once a day per org. A retention window nobody applies is not
  a retention window; the admin panel's button is the same operation by hand.

To run the sweep now rather than waiting for its hour:

```bash
docker compose -f docker-compose.prod.yml exec worker python scripts/run_sweep.py
```

### The queue

Redis lists, with the standard reliable pattern: `BRPOPLPUSH` into a
processing list, a lease key as the heartbeat, `LREM` to ack. A worker killed
mid-job leaves its payload in `processing` with an expired lease, and the
maintenance loop puts it back. Delivery is therefore at-least-once, which is
why every job body is idempotent.

Deliberately not Celery/RQ: three job types, a volume of N-per-day, and a
product whose claim is that it does nothing behind the employee's back. Take
the dependency when job volume justifies fan-out across machines, or when jobs
start needing chaining and backoff curves.

Failures retry twice, then dead-letter to `workwell:jobs:dead` (capped at 500):

```bash
redis-cli LRANGE workwell:jobs:dead 0 10
```

### Notifications

An intervention that only exists in a database row is not an intervention.
`NOTIFICATION_CHANNEL` is `log` by default so a fresh install never emails
staff before an admin has chosen to; set it to `smtp` or `webhook` and
configure `APP_BASE_URL`.

Whatever the channel, **the message says only that something is waiting, never
what**. Work email is not a private channel — it is archived, scanned by DLP,
synced to phones on desks, and in most jurisdictions readable by the employer.
Naming the finding in the subject line would disclose it to everyone with
mailbox access. `tests/unit/test_notifications.py` asserts this, so it breaks
loudly if someone later decides a helpful summary would improve engagement.

Employees can opt out in the Privacy Centre. That is a delivery preference,
not consent, and the UI says so: opting out of email does not opt out of
support, and withdrawing consent is the separate control that stops collection.

## Health endpoints

| Endpoint | Use it for | Touches |
|---|---|---|
| `/health/live` | container liveness probe | nothing |
| `/health/ready` | load-balancer readiness, compose healthcheck | Postgres, Redis, schema version, worker heartbeat |
| `/health` | humans | Postgres, Redis |

Point liveness at `/health/live`, not at a dependency check: a brief Postgres
blip should not restart every replica, turning a recoverable outage into an
outage plus a thundering herd.

`/health/ready` includes the schema check, and returns 503 when the applied
Alembic revision is behind the code's head — a replica rolled out ahead of its
migration is exactly the state that looks healthy and corrupts data. The
worker's heartbeat is reported but does not gate readiness: the API serves
stored analyses fine without a worker, and jobs queue rather than being lost.

The worker exposes its own scrape target on `WORKER_METRICS_PORT` (9100):
`/metrics` and `/health/live`. Without it, job counters and durations are
recorded into a registry in a process nothing scrapes — a worker whose jobs all
dead-letter would look exactly like a worker with nothing to do.

## Org policy that actually applies

Three admin settings were previously stored, returned by the API and rendered
in the admin panel, and consulted by nothing. They are enforced now, in one
place (`apps/backend/services/org_policy.py`):

- `disabled_sources` — strips fields on ingest, blocks the consent API from
  enabling them, and shows in the Privacy Centre as *off org-wide*, kept
  visually distinct from *never collected*: "WorkWell never collects this" and
  "your employer turned this off" are different promises.
- `interventions_enabled` — off is observe-only. Analyses still run and
  employees still see their own dashboards; nothing nudges them. Some rollouts
  need this while a works council reviews them.
- `allowed_integrations` — an allowlist. Empty means *no restriction*, not
  *nothing allowed*, since a fresh org's settings row is created with defaults.

Policy only ever subtracts collection. No admin setting can switch a source on
for an employee who declined it, and an employee can always withdraw consent
regardless of org policy.

## Leavers

Deactivate them in Administration → People. Deactivation stops the daily
analysis and invalidates any token already issued (checked per request, not
only at login). Continuing to profile someone after they leave is both
pointless and outside the consent they gave. Their history stays until the
retention window expires it.

## CI

`.github/workflows/ci.yml` runs ruff, `scripts/preflight.py`, the migrations
against an empty database, `scripts/check_migrations.py`, and the full suite
against real Postgres (pgvector) and Redis — plus the frontend typecheck and
production build.

`check_migrations.py` matters more than it looks: the test suite builds its
schema with `create_all`, so the migrations are never exercised by a test. A
column added to a model without a migration passes everything locally and
breaks the deploy.

## Desktop agents

Each machine holds its own token, provisioned by the employee in Privacy
Centre → Your devices and shown exactly once. The token is bound to one
account server-side, so an agent can only ever write telemetry for the person
who registered it; a mismatch is a 403, not a silent write.

This replaced a single shared secret that every install held, with the agent
naming in the request body which employee it was reporting for. Anyone who
could read an agent config — a file on their own laptop — could post
fabricated telemetry as a colleague, in a product whose entire output is a
statement about an individual's work pattern.

Consequences for an existing deployment:

- **Every installed agent stops working on upgrade.** There is no migration
  path, deliberately: the old credential could write for anyone. Employees
  re-register their machines from the Privacy Centre.
- Deactivating someone in Administration → People also stops their machine
  reporting, not only their login.
- Revoking a device (lost laptop, a machine handed back) takes effect on the
  next request. Tokens are stored as SHA-256 digests, so a database dump does
  not yield working credentials.
