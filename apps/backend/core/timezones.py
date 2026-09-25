"""Which day it is, for a particular person.

The unit of analysis in this product is a day: baselines compare whole
days, the persistence rule counts consecutive days, and the sweep runs
once a day. A boundary drawn in the wrong place is therefore not a
display detail. Someone in Auckland at 02:00 UTC is already at 15:00 the
next day - draw their boundary in UTC and their dashboard shows the day
before last while their actual yesterday is treated as still running.

Stored as an IANA name rather than an offset because offsets move twice a
year and a stored `+13:00` is wrong for half of it.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger("workwell.timezones")

DEFAULT_TIMEZONE = "UTC"


def resolve(name: str | None) -> ZoneInfo:
    """Never raises. A bad timezone should degrade to UTC - which is what
    the system did before anyone could set one - rather than break an
    employee's dashboard."""
    if not name:
        return ZoneInfo(DEFAULT_TIMEZONE)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("unknown timezone %r, falling back to UTC", name[:64])
        return ZoneInfo(DEFAULT_TIMEZONE)


def is_valid(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def today_in(name: str | None, now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(resolve(name)).date()
