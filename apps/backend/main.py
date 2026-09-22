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
    if not settings.ai_configured and not settings.is_test:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. WorkWell AI requires a Gemini API key to start - "
            "add it to your .env file. Set APP_ENV=test to bypass this for automated testing."
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

    return app


app = create_app()
