# WorkWell AI — working notes

Employee wellness early-warning. Detects sustained changes in a person's
*own* work pattern and offers workplace support. What makes it defensible
is what it refuses to do, so most of the rules below are about that.

## The one idea

Every comparison is against that employee's own history, never a
population. Employee E in the demo data works consistently long hours and
is correctly left alone; a population model spends 77% of its alerts on
people like them (`scripts/run_evaluation.py`). If a change would make the
system compare people to each other, it is the wrong change.

## Invariants — do not break these without saying so loudly

- **Detection is deterministic.** `ml/` computes every number: baselines,
  anomaly, persistence, risk fusion. The LLM in `agents/` only turns those
  numbers into sentences and picks from a fixed intervention table. Never
  let a model decide a score, a state, or the next step.
- **Median and MAD, never std.** `ml/anomaly/zscore.py` deliberately has no
  std fallback: std inflates from the same outliers that should be firing,
  so the z-score decays exactly when persistence should be accumulating.
- **Five consecutive days** (`PERSISTENCE_MIN_DAYS`) before anything counts.
  This is what separates a changed pattern from a busy Tuesday, and it is
  why "real-time detection" is a contradiction here.
- **A day in progress is not comparable.** `baseline_service.is_complete_day`
  excludes it, in the employee's own timezone. Without that, every metric
  the morning has not produced yet reads as −100%.
- **Consent gates twice** — on-device (`ConsentGate`) and server-side
  (`FIELD_GATES` in `telemetry_service.consent_map`). Org policy may only
  ever *subtract* collection; nothing can switch a source on for someone
  who declined it.
- **Four sources are never collectible in code**: webcam, raw keyboard,
  message content, audio. The consent API returns 400, not a greyed toggle.
- **Managers see aggregates only**, with a hard floor of 5 distinct
  contributors per metric (`ml/aggregation/cohort.py`). An admin may raise
  the floor, never lower it.
- **Safety is a separate pipeline.** `safety/` reads explicit chat content
  only, never telemetry, and never depends on the model being reachable.

## Shape

```
ml/              the deterministic core - features, baseline, anomaly, risk, evaluation
agents/          orchestrator + per-step agents + provider abstraction
apps/backend/    FastAPI: api/routes, services/, repositories/, models/, core/
apps/worker/     job queue, daily sweep, retention sweep - what makes it run itself
apps/frontend/   React + TS + Vite + Tailwind
apps/desktop-agent/  local collector; selftest.py checks what works per OS
rag/, safety/, integrations/, shared/, database/, scripts/, tests/
```

## Things that have bitten, so check them

- **Narration degrades silently by design.** A bad key, a 429, a wrong
  request shape — all produce canned fallback text while health checks stay
  green. `make smoke-provider` is the only way to know the model path works.
- **Embeddings from two models are not comparable** and pgvector will not
  tell you: it ranks them and returns confident nonsense. Chunks record
  `embedding_model`; re-run `scripts/ingest_knowledge.py` after any provider
  change.
- **The test suite builds its schema with `create_all`**, so migrations are
  never exercised by a test. `scripts/check_migrations.py` catches drift;
  CI runs it.
- **`make preflight`** catches what a Docker build would: a package the
  image's code imports but the Dockerfile never copies. Both real omissions
  (`safety`, `apps/worker`) shipped that way.
- **The `eyebrow` CSS class uppercases headings**, so `inner_text` returns
  "PEOPLE" not "People". Three browser assertions have failed on this.
- **Never name a colour in a component.** Every surface, text and signal
  colour is a token in `index.css`, redefined per theme; that is why
  adding the light theme touched one file and a handful of literal hexes.
  Each of those hexes was a white-on-white bug waiting for the switch.
- **The boot script in `index.html` sets an inline background on `<html>`**
  so first paint is the right colour. That stops the body background
  propagating to the canvas - which silently broke a `z-index: -1`
  pseudo-element carrying the ambient field, because the body's own
  background then paints over it. The field lives on `body`'s
  `background-image` for that reason.
- **Fonts are served from `public/fonts`, not fonts.googleapis.com.** A
  third-party request on every page view, from this product, was the wrong
  default. One file per subset: Plex Sans is a variable font, so Google's
  per-weight URLs are the same bytes repeated.
- **Check contrast, don't eyeball it.** The light theme's faintest text
  landed at 3.4:1 and looked fine in a screenshot.
- **Drive the UI in a browser for anything user-facing.** Every round of it
  has found something the 280-test suite and TypeScript could not —
  metric bars pinned at 100%, −100% on unreported metrics, duplicate cards,
  absurd percentage units.

## Running it

```bash
make preflight        # deploy config, without a Docker daemon
pytest tests -q       # needs Postgres + Redis; AI_PROVIDER=local
python -m apps.worker # the daily sweep; without it nothing is analysed
```

`AI_PROVIDER=local` runs everything offline against a deterministic mock —
that is what the suite uses, and it is a supported way to run the product,
not only a test mode. The app refuses to start only for
`AI_PROVIDER=gemini` with no key, since that configuration believes it is
generating text and silently is not. `docs/going-live.md` covers real keys;
`docs/deployment.md` covers operating it.

## The interface

Two themes off one set of tokens: dark is blue and white, light is black
and white. Surfaces are glass — translucent, blurred, with a lit top edge
over an ambient field on the body background. The only colour in the light
theme is a status signal (`attention`, `positive`), because weight and size
cannot carry "this is flagged" on their own.

The theme follows the operating system until someone picks one, and then
stops following it: a reader who chose light at 09:00 should not be
dropped into dark at dusk.

## Style

Comments explain *why*, especially where the obvious implementation is
wrong (the std fallback, the fixed workflow, the cohort floor). Tests are
named as the sentence they prove. Nothing that reaches an employee should
imply a diagnosis, a score, or a comparison to a colleague.
