"""Fail if the migrations have drifted from the models.

The test suite builds its schema with `Base.metadata.create_all`, which
is fast and convenient and means the migrations are never exercised by a
single test. A column added to a model without a migration therefore
passes everything locally and breaks the deploy - which is precisely how
`is_active` could have shipped.

    python scripts/check_migrations.py

Expects a database already migrated to head.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

import apps.backend.models  # noqa: E402,F401  (registers every table on Base)
from apps.backend.core.config import get_settings  # noqa: E402
from apps.backend.core.database import Base  # noqa: E402

# Alembic reports these as differences on every run for reasons that are
# not drift: server-side defaults it cannot introspect identically, and
# types it round-trips through a different spelling.
IGNORED_KINDS: set[str] = set()


def main() -> int:
    settings = get_settings()
    engine = create_engine(settings.database_url)

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        diff = [d for d in compare_metadata(context, Base.metadata) if d[0] not in IGNORED_KINDS]

    engine.dispose()

    if not diff:
        print("migrations match the models")
        return 0

    print("the models and the migrations have drifted:\n")
    for entry in diff:
        print(f"  {entry}")
    print("\nGenerate a migration with:")
    print("  alembic -c database/migrations/alembic.ini revision --autogenerate -m '...'")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
