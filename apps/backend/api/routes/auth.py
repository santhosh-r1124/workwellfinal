from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_current_user, get_db
from apps.backend.core.config import get_settings
from apps.backend.core.security import create_access_token, verify_password
from apps.backend.models import Role, User
from apps.backend.repositories import user_repo
from shared.constants.demo import DEMO_EMAIL_DOMAIN, DEMO_PASSWORD

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = user_repo.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        # Same generic wording as a bad password: whether an account exists
        # and is merely deactivated is not something an unauthenticated
        # caller should be able to probe.
        raise HTTPException(status_code=401, detail="Invalid credentials")
    role = db.get(Role, user.role_id)
    token = create_access_token(subject=user.id, extra_claims={"role": role.name if role else None})
    return LoginResponse(access_token=token, user_id=user.id, role=role.name if role else "")


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = db.get(Role, user.role_id)
    return MeResponse(id=user.id, email=user.email, full_name=user.full_name, role=role.name if role else "")


class DemoAccount(BaseModel):
    email: str
    role: str
    password: str


# The order a visitor should try them in, rather than alphabetical.
_DEMO_ROLE_ORDER = {"employee": 0, "manager": 1, "admin": 2}


@router.get("/demo-accounts", response_model=list[DemoAccount])
def demo_accounts(db: Session = Depends(get_db)):
    """The fixture accounts this deployment actually has, if any.

    The login page used to hardcode three of them and their shared
    password. Purge the fixtures - which every real install should, since
    invented patterns must not share a database with measured ones - and
    the first screen of the product carried on offering credentials that
    no longer authenticated. That reads as a broken login, not as a
    cleaned database.

    Two things keep this from being a credential endpoint: it lists only
    accounts on the fixture domain, and it says nothing at all in
    production. A real account can never appear here.
    """
    if get_settings().is_production:
        return []

    rows = db.execute(
        select(User.email, Role.name)
        .join(Role, Role.id == User.role_id)
        .where(User.email.ilike(f"%{DEMO_EMAIL_DOMAIN}"), User.is_active.is_(True))
    ).all()

    accounts = [
        DemoAccount(email=email, role=role or "", password=DEMO_PASSWORD) for email, role in rows
    ]
    return sorted(accounts, key=lambda a: (_DEMO_ROLE_ORDER.get(a.role, 9), a.email))
