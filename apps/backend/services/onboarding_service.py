"""Creating a real organisation and real people.

Until now the only path to a user was `database/seeds/seed_demo.py`:
seven fixtures on `@demo.workwell.ai` sharing one published password, and
thirty days of synthetic telemetry generated to match. Useful for looking
at the product, useless for running it - there was literally no way to
onboard a real company.

Passwords are generated here rather than chosen by whoever runs the
command. A bootstrap password typed at a terminal is the one everybody
reuses, and this one is the first admin of a system holding wellbeing
data. It is shown exactly once, like a device token, and the account can
change it at `POST /me/password`.
"""

from __future__ import annotations

import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.backend.core.security import hash_password
from apps.backend.models import Organization, Role, User
from shared.enums.roles import RoleName

# Ambiguous characters removed: this gets read off a screen and typed, and
# a bootstrap credential nobody can transcribe gets replaced with "admin".
ALPHABET = "".join(set(string.ascii_letters + string.digits) - set("O0oIl1"))
PASSWORD_LENGTH = 20


class OnboardingError(RuntimeError):
    pass


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def ensure_roles(db: Session) -> dict[str, Role]:
    roles = {}
    for name in (RoleName.EMPLOYEE, RoleName.MANAGER, RoleName.ADMIN):
        role = db.scalar(select(Role).where(Role.name == name.value))
        if role is None:
            role = Role(name=name.value, description=f"{name.value} role")
            db.add(role)
            db.commit()
            db.refresh(role)
        roles[name.value] = role
    return roles


def email_taken(db: Session, email: str) -> bool:
    # Case-insensitive: nobody expects Sam@ and sam@ to be two accounts,
    # and the unique index alone would let them be.
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower())) is not None


def create_organization(db: Session, org_name: str, admin_email: str, admin_name: str) -> tuple[Organization, User, str]:
    """The first admin of a new organisation. Returns the plaintext
    password once; it is never stored or recoverable."""
    org_name = org_name.strip()
    admin_email = admin_email.strip().lower()

    if not org_name:
        raise OnboardingError("Organisation name is required")
    if "@" not in admin_email:
        raise OnboardingError(f"{admin_email!r} is not an email address")
    if db.scalar(select(Organization).where(func.lower(Organization.name) == org_name.lower())):
        raise OnboardingError(f"An organisation called {org_name!r} already exists")
    if email_taken(db, admin_email):
        raise OnboardingError(f"{admin_email} already has an account")

    roles = ensure_roles(db)

    org = Organization(name=org_name)
    db.add(org)
    db.commit()
    db.refresh(org)

    password = generate_password()
    admin = User(
        org_id=org.id,
        email=admin_email,
        full_name=admin_name.strip() or admin_email,
        hashed_password=hash_password(password),
        role_id=roles[RoleName.ADMIN.value].id,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    return org, admin, password


def create_person(
    db: Session,
    org_id: str,
    email: str,
    full_name: str,
    role_name: str,
    team: str | None = None,
) -> tuple[User, str]:
    """An admin adding a colleague. Same one-time-password shape as the
    bootstrap: the admin passes it on, the person changes it."""
    email = email.strip().lower()

    if "@" not in email:
        raise OnboardingError(f"{email!r} is not an email address")
    if role_name not in {r.value for r in RoleName}:
        raise OnboardingError(f"Unknown role {role_name!r}")
    if email_taken(db, email):
        raise OnboardingError(f"{email} already has an account")

    roles = ensure_roles(db)
    password = generate_password()

    person = User(
        org_id=org_id,
        email=email,
        full_name=full_name.strip() or email,
        hashed_password=hash_password(password),
        role_id=roles[role_name].id,
        team=(team or None),
    )
    db.add(person)
    db.commit()
    db.refresh(person)

    return person, password
