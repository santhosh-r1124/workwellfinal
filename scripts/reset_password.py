"""Reset an account's password from the server.

There is no "forgot password" flow in this product - a reset link needs
working email, which is optional here, and a wellness tool that cannot be
installed without SMTP is worse than one that needs a shell command in the
rare case. So this is the break-glass, and the case it exists for is
specific: a self-hosted install whose only administrator has lost their
password. Without it that organisation is locked out permanently, since
nobody else can create an admin either.

Requires database access, which means it requires being the operator.
That is the authorisation.

    python scripts/reset_password.py --email ada@northwind.example
    python scripts/reset_password.py --email ada@… --list-admins
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select  # noqa: E402

from apps.backend.core.database import session_scope  # noqa: E402
from apps.backend.core.security import hash_password  # noqa: E402
from apps.backend.models import Organization, Role, User  # noqa: E402
from apps.backend.services.onboarding_service import generate_password  # noqa: E402
from shared.enums.roles import RoleName  # noqa: E402


def list_admins() -> int:
    with session_scope() as db:
        rows = db.execute(
            select(User.email, Organization.name, User.is_active)
            .join(Role, Role.id == User.role_id)
            .join(Organization, Organization.id == User.org_id)
            .where(Role.name == RoleName.ADMIN.value)
            .order_by(Organization.name, User.email)
        ).all()

    if not rows:
        print("no administrators exist - create an organisation with scripts/create_org.py")
        return 1

    for email, org_name, active in rows:
        print(f"  {email:40} {org_name:24} {'active' if active else 'DEACTIVATED'}")
    return 0


def reset(email: str, reactivate: bool) -> int:
    email = email.strip().lower()

    with session_scope() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if user is None:
            print(f"error: no account for {email}", file=sys.stderr)
            return 1

        password = generate_password()
        user.hashed_password = hash_password(password)

        was_inactive = not user.is_active
        if was_inactive and reactivate:
            user.is_active = True

        db.commit()
        label = user.email

    print(f"\naccount   {label}")
    print(f"password  {password}")
    if was_inactive:
        print(
            "\nThis account is deactivated"
            + (" - reactivated." if reactivate else ", so the new password will not let it in.")
            + (" " if reactivate else " Pass --reactivate to turn it back on.")
        )
    print("\nShown once. Any existing session for this account keeps working until its")
    print("token expires; rotate APP_SECRET_KEY if you need every session cut now.\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", help="the account to reset")
    parser.add_argument(
        "--list-admins", action="store_true", help="show every administrator, to find the right one"
    )
    parser.add_argument(
        "--reactivate", action="store_true", help="also turn a deactivated account back on"
    )
    args = parser.parse_args()

    if args.list_admins:
        return list_admins()
    if not args.email:
        parser.error("--email is required unless --list-admins")
    return reset(args.email, args.reactivate)


if __name__ == "__main__":
    raise SystemExit(main())
