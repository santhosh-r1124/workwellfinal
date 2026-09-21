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

    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "workwell"
    postgres_user: str = "workwell"
    postgres_password: str = "workwell"

    # Redis
    redis_url: str = "redis://redis:6379/0"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
