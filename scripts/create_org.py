"""Create a real organisation and its first administrator.

This is how a real deployment starts. `database/seeds/seed_demo.py` is the
other way and must never be used for one: it creates seven fixtures on
@demo.workwell.ai sharing a password published in the README, and
`generate_demo_data.py` then invents thirty days of telemetry for them.

    python scripts/create_org.py --org "Acme Ltd" --admin sam@acme.example

The password is generated, shown once, and never stored in recoverable
form. Whoever runs this changes it at first login, or hands it over and
the recipient does.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.backend.core.database import session_scope  # noqa: E402
from apps.backend.services.onboarding_service import (  # noqa: E402
    OnboardingError,
    create_organization,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", required=True, help="organisation name")
    parser.add_argument("--admin", required=True, help="first administrator's email")
    parser.add_argument("--name", default="", help="their full name (defaults to the email)")
    args = parser.parse_args()

    try:
        with session_scope() as db:
            org, admin, password = create_organization(db, args.org, args.admin, args.name)
            # Read inside the session. Once it closes these are detached
            # and every attribute access raises - which is how this
            # script failed the first time it was ever run for real.
            org_name, admin_email = org.name, admin.email
    except OnboardingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"\norganisation  {org_name}")
    print(f"administrator {admin_email}")
    print(f"password      {password}")
    print(
        "\nShown once and not recoverable. Sign in, change it at Settings, then add\n"
        "your people from Administration -> People. Nobody sees anything on their\n"
        "dashboard until their own baseline has a week of their own data.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
