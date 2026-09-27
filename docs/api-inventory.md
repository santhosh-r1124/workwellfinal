# API inventory

Every external service this codebase actually calls, and nothing it
doesn't. `docs/going-live.md` covers the same ground as a walkthrough; this
is the reference table — one block per integration, in the format used to
audit third-party dependencies.

An integration appears here only if code in this repository makes a
network call to it. Four connectors are *declared* (Microsoft 365, Slack,
Jira, GitHub) but never call out anywhere — see the end of this file for
why they're listed separately.

---

## Gemini (Google AI)

```
PURPOSE:              Turns the numbers ml/ computes into sentences, and
                       embeds text for the knowledge-base retriever (RAG).
                       Never computes a score, a state, or a next step —
                       see CLAUDE.md's invariants.
FREE TIER:            Yes, at ai.google.dev.
API KEY REQUIRED:     Yes, for this provider. Not required at all if
                       AI_PROVIDER=local (see below).
ENVIRONMENT VARIABLE: GEMINI_API_KEY
RATE LIMIT:           Provider-defined; paced client-side via
                       LLM_REQUESTS_PER_MINUTE (default 10, shared across
                       processes through Redis).
USED BY:              agents/providers/gemini_provider.py, via
                       agents/providers/factory.py
FAILURE BEHAVIOR:     A transient error (429/5xx) is retried with backoff
                       (LLM_MAX_RETRIES, default 3). An exhausted retry, a
                       bad key, or an unreachable host falls back to a
                       sentence built directly from the measured evidence
                       (agents/narration.py:safe_generate). The reply is
                       marked degraded, and degraded_reason distinguishes
                       "unreachable" from "not_configured" — see below.
                       /health reports ai: not_configured or connected,
                       never failing the process either way.
ALTERNATIVE:          AI_PROVIDER=local — a deterministic offline stand-in
                       (agents/providers/local_provider.py) that computes
                       nothing with a model: generate() returns a fixed
                       string and embed() returns a hash projection. It
                       explicitly declares generates_text = False, which is
                       what stops that fixed string from ever being shown
                       to an employee as if a model had written it (see
                       tests/integration/test_narration_honesty.py).
                       agents/providers/openai_provider.py exists as a
                       typed extension point and is unimplemented — see the
                       Not Implemented section.
```

**Why the key is optional, not a fallback path treated as broken:** every
number on the dashboard — baseline, deviation, persistence, the pattern
state — is computed by `ml/`, independently of any model. The key only
buys prose. `AI_PROVIDER=local` is a first-class supported configuration
(`apps/backend/main.py`'s startup check only refuses `AI_PROVIDER=gemini`
with no key — see `docs/going-live.md` §1). What was actually broken
before this pass: with no key configured, the stand-in's placeholder
string was being marked `narrated: true` and delivered as if it were
generated text. Fixed — see `agents/narration.py` and the honesty test
above.

---

## Desktop agent (no external API — self-hosted telemetry)

```
PURPOSE:              Reports working-hours, break, focus, context-switch,
                       and typing-rhythm signals from the employee's own
                       machine every WORKWELL_REPORT_INTERVAL_SECONDS
                       (default 300s).
FREE TIER:            N/A — not a third-party service. Runs entirely
                       against this application's own backend.
API KEY REQUIRED:     No. Uses a per-device bearer token the employee
                       generates themselves (Privacy Centre → Your
                       devices), bound server-side to one account.
ENVIRONMENT VARIABLE: WORKWELL_AGENT_TOKEN, WORKWELL_EMPLOYEE_ID,
                       WORKWELL_BACKEND_URL (set on the employee's machine,
                       not the server)
RATE LIMIT:           None beyond the report interval; each post is one
                       request against the general API rate limit
                       (120/min per identity — apps/backend/middleware/
                       security.py).
USED BY:              apps/desktop-agent/main.py →
                       POST /telemetry/report (apps/backend/api/routes/
                       telemetry.py, authenticated via
                       Depends(authenticated_device))
FAILURE BEHAVIOR:     Best-effort per-OS collector (win32gui / AppKit /
                       xdotool). A collector that isn't available on the
                       running platform returns None for that field rather
                       than crashing the agent — apps/desktop-agent/
                       selftest.py reports what actually works before a
                       rollout.
ALTERNATIVE:          None needed — this is the product's own telemetry
                       path, not a third party.
```

---

## Calendar — ICS subscribe URL (Google / Outlook / Apple)

```
PURPOSE:              Meeting-load signal (minutes per day). Only start
                       and end times are read; summaries, attendees,
                       locations, and descriptions are parsed and
                       discarded before anything is stored — a test
                       (tests/... calendar ...) asserts the event title
                       never reaches the database.
FREE TIER:            Fully free — this is a feature of the calendar
                       product the employee already has, not a paid API.
API KEY REQUIRED:     No. The employee supplies their own private
                       "secret address in iCal format" — a bearer
                       credential for their calendar, which is why it's
                       added and removed from Privacy Centre (an employee
                       screen), never from Administration.
ENVIRONMENT VARIABLE: None — stored per-employee in the database, as
                       Fernet ciphertext keyed off APP_SECRET_KEY. Shown
                       back only as a redacted fragment
                       (apps/backend/core/crypto.py:redact).
RATE LIMIT:           Whatever the calendar provider imposes on fetching
                       an .ics export; not documented by any of the three
                       providers as a hard number.
USED BY:              integrations/ics_connector.py, synced ahead of the
                       daily analysis (apps/worker/scheduler.py) so the
                       day's meeting load is present before the pattern is
                       computed, plus a manual "Sync now" in the UI.
FAILURE BEHAVIOR:     Gated by the employee's own calendar_metadata
                       consent — off by default; connecting a calendar
                       while consent is off collects nothing and the card
                       says so rather than appearing to work. A fetch
                       failure surfaces to that connector's row rather
                       than failing the whole sync.
ALTERNATIVE:          Microsoft 365 Calendar via OAuth (declared, not
                       implemented — see below) would replace this for
                       organisations that want it centrally managed
                       instead of per-employee.
```

**Network-layer note:** the server fetches a URL the employee chose, which
is the shape of SSRF. `integrations/url_guard.py` requires HTTPS, resolves
every address, refuses private/loopback/link-local/reserved ranges,
re-validates each redirect hop, and caps the download at 5MB. That closes
the obvious paths; it cannot close the gap between the DNS check and the
connect from inside the application alone — an egress allowlist at the
container level is the real control on infrastructure with instance
metadata worth stealing.

---

## Not implemented — Microsoft 365 Calendar, Slack, Jira, GitHub

```
PURPOSE:              Would add calendar/conversation/task/commit context.
                       None would add new detection ability — the ICS
                       connector and desktop agent already cover
                       everything ml/ uses.
FREE TIER:            App registration is free in all four; each needs
                       admin-consented OAuth scopes in the customer's own
                       tenant, which cannot be reduced to an API key.
API KEY REQUIRED:     N/A — OAuth client credentials, not a key.
ENVIRONMENT VARIABLE: Declared but unread in production:
                       tenant_id/client_id/client_secret (Microsoft 365),
                       client_id/client_secret (Slack),
                       site_url/client_id/client_secret (Jira),
                       app_id/installation_id/private_key (GitHub).
RATE LIMIT:           N/A — not called.
USED BY:              integrations/oauth_connectors.py declares each with
                       its required scopes and metadata; Administration →
                       Connectors lists them as "requires setup" rather
                       than hiding them.
FAILURE BEHAVIOR:     fetch_daily_features() raises ConnectorNotConfigured
                       unconditionally (integrations/oauth_connectors.py) —
                       every one of these connectors refuses to run rather
                       than returning empty or fabricated data. The 400 the
                       API returns names which connector and what it needs
                       (apps/backend/services/integration_service.py).
ALTERNATIVE:          Desktop agent + ICS calendar already deliver every
                       signal detection uses. These four are convenience
                       and additional context, not a gap in the model.
```

---

## Summary table

| Service | Free tier | Key required | Env var | Status |
|---|---|---|---|---|
| Gemini | Yes | Yes (or run keyless) | `GEMINI_API_KEY` | Implemented; live happy path unverified — needs a real key |
| Desktop agent | N/A (own service) | No — per-device token | `WORKWELL_AGENT_TOKEN` | Implemented, verified against a running backend |
| Calendar (ICS) | Yes | No — employee's own URL | none (stored encrypted) | Implemented |
| Microsoft 365 Calendar | App reg. free | OAuth, admin consent | not read in prod | Declared, refuses to run |
| Slack | App reg. free | OAuth, admin consent | not read in prod | Declared, refuses to run |
| Jira | App reg. free | OAuth, admin consent | not read in prod | Declared, refuses to run |
| GitHub | App reg. free | OAuth, admin consent | not read in prod | Declared, refuses to run |

No paid API is required to run this product. No API key is required at
all if `AI_PROVIDER=local` is acceptable for your deployment.
