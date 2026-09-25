"""Where an employee's day ends.

The unit of analysis is a day - baselines compare whole days, the
persistence rule counts consecutive days, the sweep runs once a day - so
a boundary in the wrong place is not a display detail.
"""

from datetime import date, datetime, timezone

import pytest

from apps.backend.core.timezones import is_valid, resolve, today_in

# 02:00 UTC: the hour the daily sweep runs.
SWEEP_TIME = datetime(2026, 9, 25, 2, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "zone,expected",
    [
        ("UTC", date(2026, 9, 25)),
        ("Europe/London", date(2026, 9, 25)),
        ("Asia/Kolkata", date(2026, 9, 25)),
        ("Pacific/Auckland", date(2026, 9, 25)),
        # Still the previous evening in the Americas.
        ("America/Los_Angeles", date(2026, 9, 24)),
        ("America/New_York", date(2026, 9, 24)),
    ],
)
def test_today_is_whatever_the_employee_calls_today(zone, expected):
    assert today_in(zone, SWEEP_TIME) == expected


def test_the_boundary_differs_by_a_day_across_the_globe():
    """The reason this exists: one instant, two different dates, and the
    analysis has to agree with the person rather than the server."""
    auckland = today_in("Pacific/Auckland", SWEEP_TIME)
    los_angeles = today_in("America/Los_Angeles", SWEEP_TIME)

    assert (auckland - los_angeles).days == 1


def test_an_unknown_zone_degrades_to_utc_rather_than_breaking_a_dashboard():
    assert today_in("Mars/Olympus_Mons", SWEEP_TIME) == date(2026, 9, 25)
    assert today_in("", SWEEP_TIME) == date(2026, 9, 25)
    assert today_in(None, SWEEP_TIME) == date(2026, 9, 25)
    assert str(resolve("nonsense")) == "UTC"


def test_a_naive_timestamp_is_read_as_utc_not_as_local_server_time():
    """Server local time is an accident of deployment and must never
    quietly become the reference."""
    naive = datetime(2026, 9, 25, 2, 0)

    assert today_in("America/Los_Angeles", naive) == date(2026, 9, 24)


def test_validation_accepts_iana_names_and_rejects_offsets():
    assert is_valid("Europe/Berlin") is True
    assert is_valid("UTC") is True
    # An offset is wrong for half the year; the column stores names.
    assert is_valid("+05:30") is False
    assert is_valid("Not/AZone") is False
