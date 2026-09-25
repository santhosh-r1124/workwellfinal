# Going live

What to supply, in the order it matters. Everything here has an env var
name and somewhere to get it; nothing is left as "configure your provider".

## The free path, in full

Exactly one key is needed, and it has a free tier:

| What | Cost | What it needs |
|---|---|---|
| **Gemini** | free tier at ai.google.dev | one API key |
| **Desktop agent** | free | no key at all — a per-device token the employee generates in the app |
| **Calendar (ICS)** | free | a private subscribe URL from Google, Outlook or Apple |
| Microsoft 365 / Slack / Jira / GitHub | app registration is free; needs admin consent | OAuth app in your tenant |

The first three need no developer account, no billing details and no
admin approval. Together they cover everything the detection model
actually uses: working hours, breaks, focus, context switching, typing
dynamics and meeting load. The OAuth four add convenience and a little
extra context, not new detection ability.

The product runs with **no key at all** — every number on the dashboard
is computed by `ml/`, independent of any model. The key buys prose.

### Staying inside a free tier

A free tier limits requests per minute, and the daily sweep hands every
employee to the worker pool at once. Left alone, the provider answers 429,
the fallback text appears, and the product degrades to canned sentences
while every health check stays green — the numbers keep being right and
the writing quietly stops happening.

So calls are paced and retried:

```bash
LLM_REQUESTS_PER_MINUTE=10   # the whole allowance, shared via Redis
LLM_MAX_RETRIES=3            # 429s and 5xx only, with backoff and jitter
LLM_MAX_WAIT_SECONDS=120     # how long a call may queue for a slot
```

The budget is shared between the API process and the worker rather than
each assuming it owns the quota. A throttled sweep still finishes — it
just takes longer — and nothing falls back to canned text on the way.
Raise `LLM_REQUESTS_PER_MINUTE` to whatever your plan actually allows;
check the current limits on Google's pricing page rather than trusting a
number written here, because they change.

A wrong key is not a throttle and is not retried: it fails on the first
attempt, so a bad credential cannot burn the quota that is already the
constraint. Watch `workwell_llm_retries_total` and
`workwell_llm_throttled_total` on `/metrics` — both climbing means the
limit is set too high for your plan.

Budget, roughly: the daily sweep costs about three calls per employee per
day (context, recommendation, and one embedding for retrieval), plus two
per chat message. Fifty employees is on the order of 150 calls a day
before anyone opens the assistant.

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

The employee pastes it themselves in **Privacy Centre → Connected
sources**. Not an admin screen: the URL is a bearer credential for their
calendar, so it is theirs to add and theirs to remove. It is stored as
Fernet ciphertext keyed off `APP_SECRET_KEY`, shown back only as a
redacted fragment, and deleted outright on disconnect.

Only start and end times are read — summaries, attendees, locations and
descriptions are parsed past and discarded, so what leaves the module is
meeting minutes per day. A test asserts the event title never reaches the
database.

Gated by the employee's `calendar_metadata` consent, which is **off by
default**. Connecting a calendar while it is off collects nothing and says
so on the card, rather than appearing to work.

Syncs run in the daily sweep ahead of the analysis, so the day's meeting
load is present when the pattern is computed rather than a day late.
There is a *Sync now* button for impatience.

**One thing to set at the network layer.** The server fetches a URL the
employee chose, which is the shape of SSRF. `integrations/url_guard.py`
requires https, resolves every address and refuses private, loopback,
link-local and reserved ranges, re-validates each redirect hop, and caps
the download. That closes the obvious paths, but nothing that resolves DNS
in the application can fully close the gap between the check and the
connect — an egress allowlist on the container is the real control if you
are running somewhere with instance metadata worth stealing.

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

**Live now, without touching the persistence rule:**

- The dashboard polls `/me/status`, a cheap token that changes only when
  something the employee would notice has changed, and refetches only
  then. It also refreshes when the tab regains focus and pauses while
  hidden. The header shows when the last reading arrived, so "nothing is
  happening" is distinguishable from "the agent stopped reporting".
- `REANALYSE_ON_INGEST=true` re-runs the analysis when telemetry lands,
  deduplicated to one run per employee per hour — so an agent reporting
  every five minutes costs the same as one reporting hourly. Set it false
  to hold spend to one analysis per employee per day.

The detection rule is untouched in both: five consecutive anomalous days
still decides, because that is what separates a change in how someone
works from a busy Tuesday.

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
