from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.backend.api.deps import get_current_user, get_db
from apps.backend.core.security import create_access_token, verify_password
from apps.backend.models import Role, User
from apps.backend.repositories import user_repo

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
