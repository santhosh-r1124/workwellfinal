"""Enqueue the daily sweep now instead of waiting for its scheduled hour.

Useful on first deploy - a freshly seeded install would otherwise show
nothing until the next scheduled run - and when verifying that the worker
is actually consuming.

    python scripts/run_sweep.py             # enqueue for every employee
    python scripts/run_sweep.py --inline    # run them here, no worker needed
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.backend.core.database import session_scope  # noqa: E402
from apps.worker.jobs import dispatch  # noqa: E402
from apps.worker.queue import get_queue  # noqa: E402
from apps.worker.scheduler import employee_ids, enqueue_daily_analysis  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inline",
        action="store_true",
        help="run each analysis in this process instead of enqueueing it",
    )
    args = parser.parse_args()

    with session_scope() as db:
        if args.inline:
            ids = employee_ids(db)
            print(f"analysing {len(ids)} employee(s) inline")
            for employee_id in ids:
                result = dispatch(db, "analyze_employee", {"employee_id": employee_id})
                print(f"  {employee_id}: {result.get('outcome')}")
            return 0

        queue = get_queue()
        enqueued = enqueue_daily_analysis(queue, db, date.today())
        print(f"enqueued {enqueued} analysis job(s); pending depth is now {queue.depth()}")
        if not queue.worker_alive():
            print("\nno worker heartbeat - nothing is consuming this queue.")
            print("Start one with `make worker`, or re-run with --inline.")
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
