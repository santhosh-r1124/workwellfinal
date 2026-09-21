from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.models import User


def get_user(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def list_users(db: Session, org_id: str | None = None) -> list[User]:
    stmt = select(User)
    if org_id:
        stmt = stmt.where(User.org_id == org_id)
    return list(db.scalars(stmt))
