import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_SECRET_KEY", "test-secret")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("AI_PROVIDER", "local")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "workwell_test")
os.environ.setdefault("POSTGRES_USER", "workwell")
os.environ.setdefault("POSTGRES_PASSWORD", "workwell")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from apps.backend.core.config import get_settings
from apps.backend.core.database import Base


def _ensure_test_database() -> None:
    settings = get_settings()
    admin_url = (
        f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/postgres"
    )
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": settings.postgres_db}
        ).first()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{settings.postgres_db}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_test_database()
    settings = get_settings()
    eng = create_engine(settings.database_url, future=True)
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, future=True)
    session = SessionLocal()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def org(db_session):
    from apps.backend.models import Organization

    organization = Organization(name="Test Org")
    db_session.add(organization)
    db_session.commit()
    return organization


@pytest.fixture()
def app_client(db_session):
    from fastapi.testclient import TestClient

    from apps.backend.api.deps import get_db
    from apps.backend.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    with TestClient(app) as client:
        yield client
