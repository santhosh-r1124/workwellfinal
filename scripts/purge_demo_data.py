"""Remove the demo organisation and everything that belongs to it.

Run this before a real deployment goes live, or after evaluating the
product with the seeded fixtures. The demo data is thirty days of
telemetry invented by a random number generator, and a wellness product
showing someone a "pattern change" that was made up is the worst thing
this repository could do - so it must not be sitting in the same database
as real people, where no screen can tell the reader which is which.

Scoped by email domain rather than "delete everything": a database that
already holds real accounts keeps them.

    python scripts/purge_demo_data.py            # show what would go
    python scripts/purge_demo_data.py --confirm  # actually delete
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, func, select  # noqa: E402

from apps.backend.core.database import session_scope  # noqa: E402
from apps.backend.models import (  # noqa: E402
    AgentRun,
    AuditLog,
    ChatMessage,
    ChatSession,
    ConnectorConfig,
    Consent,
    ConsentEvent,
    DailyFeature,
    DeviceToken,
    EmployeeBaseline,
    Feedback,
    Intervention,
    Organization,
    OrgSettings,
    PatternStateRecord,
    SafetyEvent,
    SelfReport,
    TelemetryEvent,
    User,
)
from shared.constants.demo import DEMO_EMAIL_DOMAIN  # noqa: E402

# Order matters: children before the rows they reference.
BY_EMPLOYEE = [
    ("feedback", Feedback, Feedback.employee_id),
    ("interventions", Intervention, Intervention.employee_id),
    ("agent runs", AgentRun, AgentRun.employee_id),
    ("pattern states", PatternStateRecord, PatternStateRecord.employee_id),
    ("baselines", EmployeeBaseline, EmployeeBaseline.employee_id),
    ("daily features", DailyFeature, DailyFeature.employee_id),
    ("telemetry events", TelemetryEvent, TelemetryEvent.employee_id),
    ("self reports", SelfReport, SelfReport.employee_id),
    ("device tokens", DeviceToken, DeviceToken.employee_id),
    ("connector configs", ConnectorConfig, ConnectorConfig.employee_id),
]


def demo_user_ids(db) -> list[str]:
    return list(db.scalars(select(User.id).where(User.email.ilike(f"%{DEMO_EMAIL_DOMAIN}"))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="delete rather than report")
    args = parser.parse_args()

    with session_scope() as db:
        ids = demo_user_ids(db)
        real = db.scalar(
            select(func.count(User.id)).where(~User.email.ilike(f"%{DEMO_EMAIL_DOMAIN}"))
        )

        if not ids:
            print("no demo accounts found - nothing to purge")
            print(f"({real} real account(s) in this database, untouched)")
            return 0

        counts = {
            label: db.scalar(select(func.count()).select_from(model).where(column.in_(ids)))
            for label, model, column in BY_EMPLOYEE
        }
        counts["chat messages"] = db.scalar(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.session_id.in_(select(ChatSession.id).where(ChatSession.employee_id.in_(ids)))
            )
        )
        counts["accounts"] = len(ids)

        print(f"demo accounts: {len(ids)}")
        for label, count in counts.items():
            if count:
                print(f"  {label:20} {count}")
        print(f"\nreal accounts that will not be touched: {real}")

        if not args.confirm:
            print("\nDry run. Pass --confirm to delete.")
            return 0

        # Chat first: its messages reference sessions, and safety events
        # reference messages.
        session_ids = select(ChatSession.id).where(ChatSession.employee_id.in_(ids))
        db.execute(delete(SafetyEvent).where(SafetyEvent.employee_id.in_(ids)))
        db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(session_ids)))
        db.execute(delete(ChatSession).where(ChatSession.employee_id.in_(ids)))

        for _, model, column in BY_EMPLOYEE:
            db.execute(delete(model).where(column.in_(ids)))

        db.execute(delete(ConsentEvent).where(ConsentEvent.user_id.in_(ids)))
        db.execute(delete(Consent).where(Consent.user_id.in_(ids)))
        db.execute(
            delete(AuditLog).where(
                AuditLog.actor_id.in_(ids) | AuditLog.subject_user_id.in_(ids)
            )
        )

        org_ids = list(db.scalars(select(User.org_id).where(User.id.in_(ids)).distinct()))
        db.execute(delete(User).where(User.id.in_(ids)))

        # Only drop an organisation that has nobody left in it: a real
        # account sharing the demo org must not lose its home.
        for org_id in org_ids:
            remaining = db.scalar(select(func.count(User.id)).where(User.org_id == org_id))
            if remaining:
                print(f"keeping organisation {org_id}: {remaining} real account(s) remain")
                continue
            db.execute(delete(OrgSettings).where(OrgSettings.org_id == org_id))
            db.execute(delete(Organization).where(Organization.id == org_id))

        db.commit()

    print("\npurged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
