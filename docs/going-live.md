# Going live

What to supply, in the order it matters. Everything here has an env var
name and somewhere to get it; nothing is left as "configure your provider".

## 1. The one key that changes what people read — Gemini

```bash
GEMINI_API_KEY=...            # ai.google.dev -> Get API key
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-3.8-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_EMBEDDING_DIM=768
```

Without it the product still detects patterns, still nudges, still shows
every number — the statistics are entirely independent of the model. What
you lose is the prose: every explanation falls back to a canned sentence.
That is why `/health` reports `ai: not_configured` rather than failing, and
why it is worth checking rather than assuming:

```bash
make smoke-provider
```

It makes the real generate and embed calls and tells you which worked.

**Two traps here, both now guarded — read this before you switch.**

- **Re-embed the knowledge base.** Anything ingested before you set a real
  key was embedded by the offline stand-in, whose vectors are a hash
  projection with no semantic meaning. Mixing vector spaces does not
  error — pgvector ranks them happily and returns a confident top-k of the
  wrong guidance. Each chunk now records which model produced it and
  retrieval only searches its own space, so the failure is visible rather
  than silent. Fix it with one command:

  ```bash
  python scripts/ingest_knowledge.py
  ```

  Administration → knowledge base reports `usable_chunks` and
  `stale_chunks` so you can see the state before anyone notices the advice
  has gone strange.

- **`GEMINI_EMBEDDING_DIM` must match the column.** `knowledge_chunks.embedding`
  is `VECTOR(768)`. `text-embedding-004` is 768, so the default is
  consistent. A model with different dimensions needs a migration altering
  that column — inserts fail loudly, which is the good case, but only
  after you have paid for the embeddings.

## 2. Real telemetry — the desktop agent

This is already live, not batch: the agent posts every
`WORKWELL_REPORT_INTERVAL_SECONDS` (default 300) and each post recomputes
that day's features immediately.

No API key. Each machine needs its own token, which the employee generates
themselves in **Privacy Centre → Your devices**:

```bash
WORKWELL_BACKEND_URL=https://workwell.example.com
WORKWELL_AGENT_TOKEN=wwd_...     # from Privacy Centre, shown once
WORKWELL_EMPLOYEE_ID=...         # their user id, shown alongside the token
WORKWELL_REPORT_INTERVAL_SECONDS=300
```

The token is bound to one account server-side; a device cannot report for
anyone else, and revoking it in the same screen stops that machine on its
next request.

Install: `pip install -r apps/desktop-agent/requirements.txt`, then
`python apps/desktop-agent/main.py`. The OS collectors are best-effort per
platform (win32gui / AppKit / xdotool) and degrade to `None` where
unavailable rather than crashing — worth a real run on each OS you support
before a rollout.

## 3. Calendar — no OAuth needed

The ICS connector is fully implemented and needs only a private subscribe
URL, which Google Calendar, Outlook and Apple Calendar all expose:

- Google Calendar → Settings → *Settings for my calendars* → *Secret
  address in iCal format*
- Outlook / Microsoft 365 → Settings → Calendar → Shared calendars →
  *Publish a calendar* → ICS link

Config key: `ics_path_or_url`. Only start and end times are read —
summaries, attendees, locations and descriptions are parsed past and
discarded, so what leaves the module is meeting minutes per day.

Gated by the employee's `calendar_metadata` consent, which is **off by
default**: they have to turn it on in the Privacy Centre first.

## 4. Everything else needs an OAuth app, not a key

These four are declared with the scopes they would need and refuse to run
rather than returning empty data. None can be reduced to pasting a key —
each needs an app registration and admin-consented scopes in your tenant:

| Connector | Config it needs | Scope |
|---|---|---|
| Microsoft 365 Calendar | `tenant_id`, `client_id`, `client_secret` | `Calendars.Read` |
| Slack | `client_id`, `client_secret` | conversation metadata only, never message text |
| Jira | `site_url`, `client_id`, `client_secret` | task counts and deadline density, never issue content |
| GitHub | `app_id`, `installation_id`, `private_key` | commit/PR/review counts and timestamps, never diffs |

Each returns the same privacy-preserving shape as the desktop agent —
counts and durations, never content. A connector that returned anything
richer would route around the consent model rather than extend it.

## What "real-time" can and cannot mean here

Worth being straight about, because two of these are free and one is a
different product.

**Already continuous:** ingestion. Telemetry arrives every few minutes and
the day's feature vector is recomputed on each post. Nothing is waiting for
a nightly batch to know what happened.

**Batch on purpose:** detection. A signal has to be anomalous for five
consecutive days before it counts (`PERSISTENCE_MIN_DAYS`), because that is
what separates "a change in how someone works" from "a busy Tuesday". A
detector that fires in real time on a rule that requires five days is a
contradiction; one that fires without the rule is a false-positive
generator pointed at people's wellbeing. The daily sweep is the honest
cadence for the decision, and it runs at `DAILY_ANALYSIS_HOUR_UTC`.

**What is genuinely missing, and what I would build:**

- The dashboard loads once and never refreshes. Live updates as telemetry
  lands are straightforward and worth having.
- Re-analysis currently happens daily or on a chat message. Triggering it
  when new data arrives (debounced) would mean the dashboard is never more
  than minutes stale, with the persistence rule untouched.
- `sync_connector` exists but no HTTP route exposes it and nothing stores
  an employee's connector config, so even the working ICS connector cannot
  be driven from the app yet.

## Order of operations

```bash
# 1. secrets
cp .env.example .env            # set GEMINI_API_KEY, APP_SECRET_KEY,
                                # POSTGRES_PASSWORD, CORS_ORIGINS,
                                # VITE_API_BASE_URL, APP_BASE_URL

# 2. check the config before it costs you a deploy
make preflight
make smoke-provider

# 3. bring it up
docker compose -f docker-compose.prod.yml up --build -d

# 4. real people, not the demo seed
#    (skip scripts/generate_demo_data.py in production - it writes
#     synthetic telemetry against real user rows)

# 5. embed the knowledge base with the live model
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/ingest_knowledge.py

# 6. confirm
curl -s https://workwell.example.com/health/ready
#   expect: schema: current, worker: running, ai: connected
```

Then have one person install the agent, register a device, and let it run
for a day before anyone else joins. Baselines need
`BASELINE_MIN_DAYS` (7) of history before the product says anything at
all — the first week is deliberately quiet, and that is worth telling
people in advance so silence does not read as breakage.
