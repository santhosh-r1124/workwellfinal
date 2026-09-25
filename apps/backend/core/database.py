from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from apps.backend.core.config import get_settings

settings = get_settings()

# pool_pre_ping costs one round trip per checkout and buys immunity to
# connections killed underneath us - by a Postgres failover, a proxy idle
# timeout, or a container restart. At this request volume that trade is
# obviously right. pool_recycle is the belt to its braces: it retires
# connections before an intermediary decides to.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle_seconds,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """For code outside the request cycle - jobs, the scheduler, scripts -
    where nothing else will roll back a half-finished unit of work."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
