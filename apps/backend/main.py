import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.backend.api.routes import (
    admin,
    analytics,
    auth,
    chat,
    consent,
    employees,
    google_oauth,
    health,
    me,
    metrics,
    rag,
    telemetry,
)
from apps.backend.core.config import get_settings
from apps.backend.core.observability import configure_logging
from apps.backend.middleware.observability import RequestObservabilityMiddleware
from apps.backend.middleware.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    rate_limiting_enabled,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.ai_key_required and not settings.ai_configured and not settings.is_test:
        raise RuntimeError(
            f"AI_PROVIDER={settings.ai_provider} needs GEMINI_API_KEY, which is not set. "
            "Add it to your .env file, or set AI_PROVIDER=local to run without a model at "
            "all - detection is unaffected either way, only the prose is. "
            "Set APP_ENV=test to bypass this for automated testing."
        )
    if not settings.ai_key_required and settings.is_production:
        # Refusing would be wrong - keyless is a supported way to run this -
        # but silence would not be. Every explanation an employee reads in
        # this configuration is a canned sentence, and nothing else in the
        # product says so: /health reports ai: not_configured and stays
        # green, which is exactly the kind of quiet degradation that lasts
        # for months.
        logging.getLogger("workwell").warning(
            "AI_PROVIDER=local in production: detection is unaffected, but every "
            "explanation shown to an employee is canned text, not generated."
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title="WorkWell AI", version="0.1.0", lifespan=lifespan)

    # Starlette runs the most recently added middleware outermost, so these
    # are added innermost-first: observability times the real handler,
    # rate limiting sheds load before that, security headers apply to every
    # response including 429s, and CORS wraps the lot.
    app.add_middleware(RequestObservabilityMiddleware)
    if rate_limiting_enabled():
        app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # In DEMO_MODE the UI may be opened on any local port (3000, 3300,
        # 5173...) or as 127.0.0.1; a CORS refusal there looks to the
        # presenter like "invalid credentials" and empty dashboards.
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?" if settings.demo_mode else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(auth.router)
    app.include_router(consent.router)
    app.include_router(telemetry.router)
    app.include_router(employees.router)
    app.include_router(me.router)
    app.include_router(rag.router)
    app.include_router(chat.router)
    app.include_router(analytics.router)
    app.include_router(admin.router)
    app.include_router(google_oauth.router)

    return app


app = create_app()
