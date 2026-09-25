# WorkWell AI

Employee Wellness Early-Warning & Support Platform.

```
Collects approved work-pattern signals
        v
Creates employee-specific baseline
        v
Detects persistent changes
        v
Understands workplace context
        v
Uses agentic AI to reason over evidence
        v
Retrieves trusted wellness guidance
        v
Provides an intervention to the employee
        v
Learns from feedback
```

This repository implements the core intelligence pipeline and agentic wellness layer end to
end, running against synthetic demo data out of the box: desktop-style telemetry collection ->
privacy-preserving feature engineering -> personal (not population) baselines -> robust
anomaly/persistence detection -> a fixed agent orchestration workflow (context, risk fusion,
intervention, wellness RAG) -> an employee dashboard, pattern timeline, chat assistant, and an
independent safety pipeline.

The pipeline runs **on a schedule, not on demand**. A background worker
(`apps/worker/`) analyses every consenting employee once a day and notifies them
when there is something waiting. That distinction is the product: an
early-warning system that only warns the people who think to ask is not one.

## Quick start

```bash
git clone <repository>
cd workwell-ai   # or whatever you cloned this as
cp .env.example .env
# edit .env and set GEMINI_API_KEY=<your key>
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

Five containers come up: `postgres`, `redis`, `backend`, `worker` and
`frontend`. The worker is the one that makes this run itself; without it
nothing is analysed until someone opens the assistant and asks.

The backend refuses to start without `GEMINI_API_KEY` set (Phase 0.4) - this is enforced in
`apps/backend/main.py`'s lifespan hook, not just documented.

Once the stack is up, seed demo accounts and generate synthetic data:

```bash
docker compose exec backend python database/seeds/seed_demo.py
docker compose exec backend python scripts/generate_demo_data.py
docker compose exec backend python -c "
from apps.backend.core.database import SessionLocal
from rag.ingestion.pipeline import ingest_knowledge_base
db = SessionLocal()
print('chunks ingested:', ingest_knowledge_base(db))
db.close()"
```

Then log in at http://localhost:3000/login with one of the seeded demo accounts, e.g.
`employee.b@demo.workwell.ai` / `workwell-demo` (Employee B has a synthetic "increasing overtime"
pattern and will show a detected pattern change on the dashboard).

Demo accounts (`database/seeds/seed_demo.py`), each mapped to a distinct synthetic archetype
(`scripts/generate_demo_data.py`, Phase 2.4):

| Account | Archetype | Expected result |
|---|---|---|
| employee.a@demo.workwell.ai | normal | STABLE |
| employee.b@demo.workwell.ai | increasing overtime | PATTERN_CHANGE (after-hours/recovery) |
| employee.c@demo.workwell.ai | meeting overload | PATTERN_CHANGE (meeting load/focus) |
| employee.d@demo.workwell.ai | fragmented work | PATTERN_CHANGE (context switching/focus) |
| employee.e@demo.workwell.ai | stable but naturally high workload | STABLE |

Employee E is the important one to point at: consistently high workload that never deviates
from *their own* baseline is correctly left alone, which is the whole point of personal
baselines over population comparisons.

Password for every seeded account: `workwell-demo`.

## Local development without Docker

Docker Compose is the intended path, but everything also runs directly against a local
PostgreSQL 16 + pgvector + Redis:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r apps/backend/requirements.txt

export POSTGRES_HOST=localhost POSTGRES_USER=workwell POSTGRES_PASSWORD=workwell POSTGRES_DB=workwell
export APP_SECRET_KEY=dev-secret GEMINI_API_KEY=<your key>
export REDIS_URL=redis://localhost:6379/0
export PYTHONPATH=$(pwd)

alembic -c database/migrations/alembic.ini upgrade head
python database/seeds/seed_demo.py
python scripts/generate_demo_data.py
uvicorn apps.backend.main:app --reload

python -m apps.worker        # in a second terminal - the daily sweep
cd apps/frontend && npm install && npm run dev
```

Without a worker running, the API falls back to computing an analysis inline on
the first request that needs one (`INLINE_ANALYSIS_FALLBACK`, on by default for
exactly this case). It detects that from the worker's heartbeat rather than
assuming, so a production deployment whose worker has died does not silently
start blocking requests instead.

To run the daily sweep immediately rather than waiting for its scheduled hour:

```bash
python scripts/run_sweep.py            # enqueue for a running worker
python scripts/run_sweep.py --inline   # or just run them here
```

Set `AI_PROVIDER=local` instead of a real Gemini key to run everything (including the demo data
generator and RAG ingestion) fully offline against a deterministic mock provider - useful for
development and is what the automated test suite uses.

**Moving to live data and real keys:** [docs/going-live.md](docs/going-live.md) lists every
credential, where to get it, and the two traps on the way - chiefly that anything embedded before
you set a real key was embedded by the offline stand-in, and mixing vector spaces returns
confidently wrong guidance rather than an error. `python scripts/ingest_knowledge.py` after any
provider change.

## Architecture

```
                     React Frontend (Vite/TS/Tailwind)
                              |
                        FastAPI Backend
                              |
          +-------------------+-------------------+
          v                   v                   v
     PostgreSQL             Redis            Agent Orchestrator
     + pgvector                                    |
                                        +-----------+-----------+
                                        v                       v
                                Deterministic ML          Gemini-backed
                                (ml/): baseline,          agents (agents/):
                                anomaly/persistence,      context, intervention,
                                risk fusion                wellness, RAG synthesis
```

Detection is deliberately **not** LLM-driven: baselines, anomaly detection, persistence, and
risk fusion (`ml/`) are robust statistics and rule-based fusion. The LLM (`agents/`, via the
`AIProvider` abstraction in `agents/providers/`) only explains evidence the deterministic layer
already computed, proposes the least-intrusive intervention from a fixed rule table, and
synthesizes the final wellness message using retrieved guidance (`rag/`). This split is what
keeps the system testable (see `tests/agents/test_agent_scenarios.py`) and keeps weak
behavioral evidence from being casually turned into a mental-health conclusion by a model that's
just trying to be helpful.

The **safety pipeline** (`safety/`, wrapped by `agents/safety_agent.py`) runs independently of
this orchestration: it is a deterministic keyword/pattern classifier over explicit chat content
only, never over telemetry, and is checked on every chat message before anything else touches it.

### Repository layout

```
apps/backend/        FastAPI app: api/ routes, services/, repositories/, models/ (SQLAlchemy), core/
apps/worker/          Redis-backed job queue, daily analysis sweep, retention sweep
apps/frontend/        React + TypeScript + Vite + Tailwind
apps/desktop-agent/    Local collector (psutil/pynput) -> privacy-preserving features -> POST /telemetry/events
agents/               Orchestrator + individual agents + the Gemini/OpenAI/Local provider abstraction
ml/                   features/, baseline/, anomaly/, risk/ - the deterministic core
rag/                  ingestion/, retrieval/, knowledge/ (seed wellness knowledge base)
safety/               Independent crisis-language classifier, policy, escalation
database/             Alembic migrations + demo seed script
scripts/              demo data, evaluation, and the operational checks:
                      preflight.py (deploy config), check_migrations.py (model drift),
                      smoke_provider.py (real model provider), run_sweep.py
shared/               Pydantic schemas / enums / constants shared across backend, agents, ml, rag
tests/                unit/, integration/, agents/ (scenario tests)
```

## What's implemented vs. deferred

All 21 roadmap phases are now implemented and tested, with the boundaries below.

**Fully built and verified:** the detection and agentic wellness pipeline (Phases 0-10), the
provider abstraction (14/15), the test suite (16), team analytics (11), the admin panel (12),
the evaluation harness (17/18), observability (19), and security hardening (20).

**Built but not executed end to end:** the production deployment config (Phase 21) -
`docker-compose.prod.yml`, the multi-stage frontend image and the nginx TLS proxy were authored
in an environment with no Docker daemon. The Python imports, migrations, tests, the worker
running its own jobs, and the frontend production build are all verified; the container
orchestration around them is not. `make preflight` now checks statically what a build would
otherwise discover expensively - every COPY source, every module a container is told to run, and
every package that code transitively imports. It was written after the backend image shipped for
weeks without `COPY safety`, which would have died on first import. See
[docs/deployment.md](docs/deployment.md).

**Partially built by necessity (Phase 13):** the integration framework, the connector registry
and a fully working ICS calendar connector are real and tested. The Microsoft Graph, Slack, Jira
and GitHub connectors are *declared, not implemented* - each requires OAuth app registration and
admin-consented scopes in a customer tenant, so there is nothing meaningful to build or test
without those credentials. They report `implemented: false` and raise on use rather than
returning empty data, so a half-configured integration can never look like a quiet one.

### Evaluation results (Phase 18)

`python scripts/run_evaluation.py` compares the shipped personalized detector against a
population-baseline detector on synthetic data. Headline numbers:

| | Personalized | Population (matched alert rate) |
|---|---|---|
| Precision | 0.96 | 0.00 |
| Recall | 0.75 | 0.00 |
| AUROC | 0.99 | 0.35 |
| Episodes detected | 13/13 | 0/13 |
| False positives on stable-high-workload employees | 0.00 | 0.77 |

The population model, forced to alert as often as the personalized one, spends 77% of its alerts
on employees whose workload is merely high and stable rather than strained, and catches none of
the real episodes. That is the exact failure mode personal baselines exist to prevent.

This is synthetic data: it measures whether the detector recovers a known generative signal, not
real-world clinical validity, which would require consented longitudinal data and validated
instruments.

Some pragmatic scope choices worth knowing about:

- The desktop agent's active-window detection (`apps/desktop-agent/collectors/window_collector.py`)
  is best-effort per-OS (win32gui / AppKit / xdotool) and returns `None` gracefully where
  unavailable (e.g. headless); the roadmap itself flags this as a "proper native app" item for
  later.
- The desktop agent used to authenticate with one shared secret while naming in the request
  body which employee it was reporting for, so anyone who could read an agent config - a file on
  their own laptop - could post fabricated telemetry as a colleague. Each device now has its own
  token, bound to one account, provisioned by the employee in Privacy Centre → Your devices and
  revocable there.
- The Gemini model/embedding model names are read from `.env` (`GEMINI_MODEL`,
  `GEMINI_EMBEDDING_MODEL`) so they can be updated without a code change as Google's available
  models evolve.
- Gemini calls have never been made against a live key - the test suite runs on the offline
  `local` provider. `make smoke-provider` exists for exactly this: it makes the real calls with
  the real key and reports which ones worked. Run it before trusting the narration, because
  graceful degradation means a wrong key no longer *fails* - it just quietly turns every
  explanation into canned text.
- The job queue is ~250 lines of explicit Redis commands rather than Celery or RQ. Deliberate
  at three job types and one-analysis-per-employee-per-day, and documented in
  `apps/worker/queue.py` with the conditions that should change the decision.

## Privacy by design

- Consent is enforced twice: the desktop agent's local `ConsentGate` avoids even computing a
  disabled signal, and the backend independently strips any disabled field from incoming
  telemetry before it is ever written to the database (`shared/constants/data_sources.py`
  `FIELD_GATES`, `apps/backend/services/telemetry_service.py`).
- Webcam, raw keyboard content, audio recording, and message content are **never collectible**
  in this product (`DataSourceKey` entries with `collectible=False`) - the consent API rejects
  attempts to enable them with a 400, not just a UI toggle that's greyed out.
- A manager can never read an individual employee's baseline/pattern/wellness data through the
  API - only the employee themselves or an org admin (`apps/backend/api/routes/employees.py`).
- A device token writes telemetry for the account it was issued to and no other, so a machine
  cannot fabricate a colleague's work pattern. The employee can see which machines are reporting
  about them and revoke any of them, without going through an administrator.
- The dashboard never surfaces a "risk score" or clinical label - only Workload/Recovery/
  Focus/Schedule/Communication, plus an explicit "data not used" list (Phase 9.2).
- `GEMINI_API_KEY` never reaches the frontend; verified in `tests/integration/test_privacy.py`.
- Notifications say only that a suggestion is waiting, never what it is. Work email is archived,
  DLP-scanned, synced to unlocked phones and in most jurisdictions readable by the employer, so
  naming the finding would disclose it to everyone with mailbox access.
  `tests/unit/test_notifications.py` asserts the absence of every leaking word, so this breaks
  loudly rather than drifting.
- Org policy (`disabled_sources`, `interventions_enabled`, `allowed_integrations`) is enforced
  in `apps/backend/services/org_policy.py`, and can only ever *subtract* collection. No admin
  setting switches a source on for an employee who declined it, and withdrawing consent is
  always permitted regardless of org policy.
- Deactivating someone stops their daily analysis and invalidates tokens already issued -
  checked per request, not only at login. Profiling an ex-employee is outside the consent they
  gave.
- A connected calendar's subscribe URL is a bearer credential, so it is stored as ciphertext,
  returned only as a redacted fragment, and deleted outright on disconnect. Only start and end
  times are read; a test asserts the event title never reaches the database. And because the
  employee chooses the URL the server fetches, `integrations/url_guard.py` refuses private and
  loopback addresses rather than letting the connector be pointed at instance metadata.

## Testing

```bash
export POSTGRES_HOST=localhost POSTGRES_USER=workwell POSTGRES_PASSWORD=workwell
export REDIS_URL=redis://localhost:6379/1
pytest tests -v
```

The suite creates and tears down a `workwell_test` database automatically and runs entirely
against `AI_PROVIDER=local` (no network / no real Gemini key required). It covers:

- `tests/unit/` - feature engineering, baseline statistics, anomaly/persistence, risk fusion,
  pattern object assembly, and the desktop agent's pure aggregation functions.
- `tests/integration/` - health check, consent API (including the "can never enable a
  never-collected source" rule), the telemetry -> daily feature -> baseline pipeline, and the
  privacy tests described above.
- `tests/agents/` - end-to-end orchestrator scenarios: normal employee, sustained overtime,
  context offered cautiously (no diagnostic language), missing data, all sensors disabled, and
  explicit safety-language classification (crisis / concern / benign).

## Key API surface

```
GET  /health/live  /health/ready         GET  /metrics (Prometheus)
GET  /health
POST /auth/login                         GET  /auth/me
GET  /consent                            POST /consent            PATCH/DELETE /consent/{source}
POST /telemetry/events                   POST /telemetry/self-report   (per-device token)
GET  /employees/{id}/baseline            GET  /employees/{id}/patterns
POST /rag/query
POST /chat

# the authenticated employee only - no id in any path or body
GET  /me/history                         GET/PATCH /me/preferences
GET  /me/interventions                   POST /me/interventions/{id}/respond
GET/POST /me/devices                     DELETE /me/devices/{id}
GET  /me/status                          GET  /me/connectors
PUT/DELETE /me/connectors/{key}          POST /me/connectors/{key}/sync
GET/POST /me/self-report

# manager or admin - aggregates only, never individuals
GET  /analytics/teams                    GET  /analytics/teams/{team}

# admin only
GET/PATCH /admin/settings                GET  /admin/audit-logs
GET  /admin/data-sources                 GET  /admin/integrations
GET  /admin/knowledge-base               POST /admin/retention/apply
GET  /admin/users                        PATCH /admin/users/{id}
```

Full interactive docs at `/docs` once the backend is running.
