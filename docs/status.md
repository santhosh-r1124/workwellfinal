# Project status

Derived from the code as it stands, not from what was intended. A feature
is marked COMPLETE only when the underlying computation or integration
actually runs end-to-end — a screen existing for it is not enough, and
several items below say so explicitly where that distinction matters.

324 tests pass (`pytest tests -q`, `AI_PROVIDER=local`). `make preflight`,
`ruff check .`, and the frontend typecheck/build are all clean as of this
pass. Verified in a running browser against real (non-synthetic) data —
see the "verified against a live install" note on each relevant feature.

---

## Detection core

**STATUS: COMPLETE**

Baseline, anomaly, and persistence are deterministic and live in `ml/`:
median/MAD (never std — `ml/anomaly/zscore.py` has no std fallback by
design), a five-consecutive-day persistence rule
(`shared/constants/wellbeing.py:PERSISTENCE_MIN_DAYS`), and per-employee
comparison only — never population (`scripts/run_evaluation.py` measures
this directly: a population model spends 77% of its alerts on people whose
own baseline is simply long hours).

What exists: feature engineering, baseline computation, anomaly scoring,
persistence tracking, pattern-state transitions, and the evaluation
harness comparing personalized vs. population models. Nothing here calls
a model — see CLAUDE.md's invariants for why that boundary is enforced in
code, not just in intent.

Verified against a live install: created a real org, registered a real
device, ran the actual desktop agent for ~95 seconds, and confirmed
measured (non-zero) telemetry produced a real `daily_features` row.

---

## AI narration

**STATUS: COMPLETE, with one behavior fixed this pass**

The model (Gemini, or `local` as a supported no-key mode) only converts
numbers `ml/` already computed into sentences — `agents/orchestrator.py`
enforces this is the only thing agents do. `safe_generate` is the single
call site for model text; it never raises, always falls back to a
sentence built from the measured evidence, and records whether narration
actually happened.

**What was fixed this pass:** with no key configured, the offline
stand-in's placeholder string — literally "[local-mode explanation] ...
Configure GEMINI_API_KEY..." — was being marked `narrated: true` and
delivered to the chat UI as if a model had generated it. Providers now
declare `generates_text` explicitly; the stand-in declares `False`, and
`safe_generate` refuses to call `.generate()` at all on a provider that
says it can't. The API also now distinguishes `degraded_reason:
"not_configured"` (a deployment choice) from `"unreachable"` (a fault
someone should look at) so the wording an employee reads is accurate
either way. See `tests/integration/test_narration_honesty.py`.

**Known limitation, unchanged by this pass:** the *live* Gemini path
(a real key actually answering) has never been exercised in this
environment — every test runs against the deterministic `local` provider.
`make smoke-provider` is the command that proves the live path works, and
it needs a real `GEMINI_API_KEY` to run.

---

## RAG (wellness knowledge base)

**STATUS: COMPLETE**

Real pgvector retrieval (`cosine_distance`), not a keyword match dressed
up as semantic search. Each chunk records which embedding model produced
it (`embedding_model` column); retrieval only searches within its own
model's space, so a provider switch fails loudly (a dimension mismatch on
insert) rather than silently (pgvector ranking two incompatible vector
spaces and returning a confident wrong answer). `scripts/ingest_knowledge.py`
re-embeds after a provider change.

**Limitation:** embeddings under `AI_PROVIDER=local` are a normalized hash
projection, not semantically meaningful — adequate for exercising the
retrieval *pipeline*, not for judging retrieval *quality*. Quality can only
be assessed once ingested with a real embedding model.

---

## Employee chat assistant

**STATUS: COMPLETE**

Not a predefined-answer lookup — there is no `if question == "...":` table
anywhere in this codebase (checked directly). Every reply is built from
that employee's own stored analysis (`_answer_from_analysis` in
`apps/backend/services/chat_service.py`): context inferred from the
pattern, a recommendation grounded in retrieved guidance, sources cited
where the RAG pipeline supplied them. The safety pipeline runs first and
independently on every message regardless of narration state (see below).

Newly hardened this pass: a failed request previously left the UI showing
nothing wrong (`InterventionCard`, `CheckIn`, `PrivacyCenter` all had
`try/finally` with no `catch`, so a failed write silently re-enabled the
form as though it had succeeded). All three now surface the failure and
say nothing was recorded.

---

## Safety pipeline

**STATUS: COMPLETE**

`safety/` reads explicit chat content only — never telemetry — and never
depends on the model being reachable (`chat_service.py`: the safety check
runs and answers even during a provider outage, ahead of the narration
path). This is architecturally separate from the wellness-narration
pipeline on purpose; a false negative here has a different cost than a
canned sentence.

---

## Consent and privacy

**STATUS: COMPLETE**

Two-sided gate: `ConsentGate` on-device, `FIELD_GATES` server-side. Org
policy can only *subtract* collection, never add it back for someone who
declined (checked directly in `telemetry_service.consent_map`). Four
sources — webcam, raw keyboard, message content, audio — are not
collectible in code at all; the consent API returns 400 for them rather
than exposing a toggle that would falsely imply it's a choice.

Hardened this pass: the consent screen's fetch and toggle both had no
error handling — a failed load rendered an *empty* list (reading as
"nothing is being collected") and a failed toggle silently left the switch
looking as though it had changed. Both now show an explicit failure state
rather than a wrong-looking success.

---

## Manager / org analytics

**STATUS: COMPLETE**

Real aggregation with a hard k-anonymity floor
(`ml/aggregation/cohort.py:ABSOLUTE_MIN_COHORT` = 5), enforced in code, not
just as a default an admin could accidentally lower — `get_min_cohort`
takes `max(configured, ABSOLUTE_MIN_COHORT)`. Below the floor, the metric
is withheld and the UI says so ("Withheld — this team has N person(s) with
data, below the minimum cohort of 5"), rather than showing a suppressed or
approximated number.

Verified against a live install: Northwind Labs' 1-person Platform team
correctly shows withheld, not a fabricated aggregate.

---

## Onboarding (real organisations)

**STATUS: COMPLETE**

`scripts/create_org.py` bootstraps a real org and admin with a generated
password (20 chars, ambiguous characters excluded — `O0oIl1`).
`POST /admin/users` adds people with their own one-time password;
`POST /me/password` lets them replace it. `scripts/reset_password.py` is
the break-glass path for a locked-out sole admin, since there's no email
reset flow.

Verified against a live install: created "Northwind Labs" with three real
accounts (admin, manager, employee) via the actual API, not a fixture
script.

---

## Demo/synthetic data controls

**STATUS: COMPLETE**

`scripts/generate_demo_data.py` refuses to run in production, and refuses
to run against any database holding an account outside the demo org
domain (`shared/constants/demo.py:DEMO_EMAIL_DOMAIN`).
`scripts/purge_demo_data.py` removes fixtures scoped by that same domain,
imported from one shared module so the seeder and the purger cannot drift
apart. The login screen's demo-account list is served by
`GET /auth/demo-accounts`, which returns nothing in production and nothing
once the fixtures are purged — it no longer hardcodes credentials that may
not exist.

---

## Real-time / freshness semantics

**STATUS: COMPLETE, and accurately labeled**

- **Continuous**: telemetry ingestion. The agent posts every
  `WORKWELL_REPORT_INTERVAL_SECONDS` (default 300s) and the day's feature
  vector is recomputed on each post — not waiting for a nightly batch.
- **Auto-refreshing**: the dashboard polls `/me/status`, a cheap version
  token, and only refetches the real payload when it changes; it also
  pauses while the tab is hidden. This is client-side polling, correctly
  not labeled "live" anywhere in the UI.
- **Batch, by design, not by limitation**: detection. Five consecutive
  anomalous days must elapse before anything is flagged
  (`PERSISTENCE_MIN_DAYS`). The UI never claims real-time detection,
  because that would be a contradiction with the rule that makes the
  product trustworthy rather than a false-positive generator.
- `REANALYSE_ON_INGEST` (default true) re-runs analysis on new telemetry,
  deduplicated to one run per employee per hour.

No UI copy in this codebase claims "real-time" for anything that isn't
either continuously ingested or genuinely re-evaluated on that cadence —
checked directly (`grep -rniE "real.?time" apps/frontend/src` matches
nothing).

---

## Interface

**STATUS: COMPLETE**

Two themes (dark: blue/white, light: black/white) on one token set in
`index.css`; no component names a raw color. Glass surfaces — translucent,
blurred, lit top edge — over an ambient field. Verified in a real browser
at desktop and phone width, in both themes, against the live Northwind
data (not screenshots of a mock).

Hardened this pass: `PatternTimeline` had no error handling at all (a
failed fetch and an empty result rendered identically); `CheckIn` and
`InterventionCard` swallowed write failures; the light theme's faintest
text measured 3.4:1 contrast (now 5:1+, checked with the actual WCAG
formula, not eyeballed).

---

## Not implemented

**STATUS: NOT IMPLEMENTED — by design, not oversight**

Microsoft 365 Calendar, Slack, Jira, GitHub. Each is declared with its
required scopes and refuses to run (`ConnectorNotConfigured`) rather than
returning empty or fabricated data. Each needs an OAuth app registered in
the customer's own tenant with admin-consented scopes — not reducible to
an API key, so there is nothing to configure from this side. See
`docs/api-inventory.md` for the exact scopes each would need.

**What would be required to implement one:** an OAuth app registration
flow (authorize → callback → token storage, encrypted like the ICS
connector's credential), the specific Graph/Slack/Jira/GitHub API calls
mapped to `fetch_daily_features()`'s existing contract
(`integrations/base.py`), and — per the consent model — ensuring each only
returns counts and durations, never content, matching what the ICS
connector and desktop agent already guarantee.

---

## Infrastructure verification

**STATUS: BLOCKED — no Docker daemon in this environment**

`make preflight` (95 checks) validates what a Docker build would catch
without needing the daemon: every package a container's code imports is
actually copied by the Dockerfile (two real omissions — `safety` and
`apps/worker` — shipped exactly this way before preflight existed), every
`${VAR:?required}` in `docker-compose.prod.yml` has a value, and every env
var the settings model reads is documented in `.env.example`. This passes
clean. **What preflight cannot check:** whether the images actually build
and start. That has never been run in this environment and is the first
thing to try before a real deploy.

CI (`.github/workflows/ci.yml`) runs the test suite and
`scripts/check_migrations.py` (catches schema drift the test suite's
`create_all` would otherwise hide) on every push.
