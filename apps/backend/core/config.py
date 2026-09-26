from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "dev-only-insecure-secret-change-me"

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    cors_origins: str = "http://localhost:3000"

    # AI
    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_embedding_model: str = "text-embedding-004"
    gemini_embedding_dim: int = 768

    # Pacing, sized for a free API tier where the binding constraint is
    # requests per minute rather than money. The budget is shared across
    # the API and the worker through Redis, so raise this to match your
    # plan's actual limit rather than per process.
    llm_requests_per_minute: int = 10
    llm_max_retries: int = 3
    llm_retry_base_seconds: float = 2.0
    # How long a call may wait for a slot before going anyway. Being
    # throttled beats silently skipping the work.
    llm_max_wait_seconds: float = 120.0

    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "workwell"
    postgres_user: str = "workwell"
    postgres_password: str = "workwell"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Database pool. Sized for the default uvicorn worker count; raise
    # together with replica count, and keep (pool_size + max_overflow) *
    # replicas under Postgres's max_connections or new replicas will fail
    # to connect under load rather than queue.
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_recycle_seconds: int = 1800

    # Background worker
    worker_concurrency: int = 2
    worker_metrics_port: int = 9100
    job_lease_seconds: int = 600
    job_max_attempts: int = 3
    # Hour (UTC) at which the daily sweep enqueues an analysis for every
    # employee. Default is after most timezones' working day.
    daily_analysis_hour_utc: int = 2
    # How stale a stored analysis may be before a chat message triggers a
    # background refresh.
    analysis_max_age_hours: int = 24
    # Re-analyse when new telemetry arrives rather than only on the daily
    # sweep. Deduplicated to one run per employee per hour, so a chatty
    # agent costs the same as a quiet one. Turn off to hold the model
    # spend to exactly one analysis per employee per day.
    reanalyse_on_ingest: bool = True
    # Run analysis inline when no worker is deployed. Correct for a
    # single-process dev or pilot install; turn off in production, where a
    # worker container runs the same jobs off the request path.
    inline_analysis_fallback: bool = True

    # Notifications
    notification_channel: str = "log"  # none | log | smtp | webhook
    app_base_url: str = "http://localhost:3000"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    notification_webhook_url: str = ""

    # Privacy
    raw_telemetry_storage: bool = False
    keyboard_content_storage: bool = False
    webcam_collection: bool = False
    audio_recording: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_test(self) -> bool:
        return self.app_env.lower() in {"test", "testing"}

    @property
    def ai_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def ai_key_required(self) -> bool:
        """Whether the configured provider needs a credential to do anything.

        `local` is the deterministic offline stand-in, and needing no key is
        the entire point of it: every number on the dashboard comes from
        `ml/`, so the product is meant to run with no model at all. Demanding
        a Gemini key regardless meant the documented keyless path exited on
        start - a container that dies at boot, in the one configuration the
        docs tell a first-time reader to try.
        """
        return self.ai_provider.strip().lower() != "local"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
