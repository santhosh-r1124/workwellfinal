"""Bootstraps a demo organization, roles, and users so the app is usable
immediately after `docker compose up`. Run with:

    python database/seeds/seed_demo.py

Safe to re-run: skips creation of rows that already exist by email/name.
"""
from apps.backend.core.database import SessionLocal
from apps.backend.core.security import hash_password
from apps.backend.models import Organization, Role, User
from shared.enums.roles import RoleName

DEMO_ORG_NAME = "WorkWell Demo Org"
DEMO_PASSWORD = "workwell-demo"

DEMO_EMPLOYEES = [
    ("employee_a", "Employee A", "employee.a@demo.workwell.ai"),
    ("employee_b", "Employee B", "employee.b@demo.workwell.ai"),
    ("employee_c", "Employee C", "employee.c@demo.workwell.ai"),
    ("employee_d", "Employee D", "employee.d@demo.workwell.ai"),
    ("employee_e", "Employee E", "employee.e@demo.workwell.ai"),
]

DEMO_ADMIN = ("admin", "Demo Admin", "admin@demo.workwell.ai")


def _get_or_create_role(db, name: str) -> Role:
    role = db.query(Role).filter_by(name=name).first()
    if role:
        return role
    role = Role(name=name, description=f"{name} role")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def _get_or_create_org(db) -> Organization:
    org = db.query(Organization).filter_by(name=DEMO_ORG_NAME).first()
    if org:
        return org
    org = Organization(name=DEMO_ORG_NAME)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _get_or_create_user(db, user_id: str, full_name: str, email: str, org_id: str, role_id: str) -> User:
    existing = db.get(User, user_id)
    if existing:
        return existing
    user = User(
        id=user_id,
        org_id=org_id,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(DEMO_PASSWORD),
        role_id=role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed() -> None:
    db = SessionLocal()
    try:
        employee_role = _get_or_create_role(db, RoleName.EMPLOYEE.value)
        _get_or_create_role(db, RoleName.MANAGER.value)  # reserved for future manager-scoped demo accounts
        admin_role = _get_or_create_role(db, RoleName.ADMIN.value)
        org = _get_or_create_org(db)

        for user_id, full_name, email in DEMO_EMPLOYEES:
            _get_or_create_user(db, user_id, full_name, email, org.id, employee_role.id)

        _get_or_create_user(db, DEMO_ADMIN[0], DEMO_ADMIN[1], DEMO_ADMIN[2], org.id, admin_role.id)

        print(f"Seeded org '{DEMO_ORG_NAME}' with {len(DEMO_EMPLOYEES)} demo employees and 1 admin.")
        print(f"Demo password for all seeded users: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
