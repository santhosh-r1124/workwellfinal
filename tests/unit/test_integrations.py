from datetime import date

import pytest

from integrations import available_connectors, get_connector
from integrations.base import ConnectorNotConfigured
from integrations.ics_calendar import IcsCalendarConnector, parse_meeting_minutes

SAMPLE_ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Confidential board discussion
DTSTART:20260210T090000Z
DTEND:20260210T100000Z
ATTENDEE:mailto:someone@example.com
LOCATION:Room 3
END:VEVENT
BEGIN:VEVENT
SUMMARY:Standup
DTSTART:20260210T140000Z
DTEND:20260210T141500Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Next day sync
DTSTART:20260211T110000Z
DTEND:20260211T120000Z
END:VEVENT
END:VCALENDAR
"""


def test_parses_meeting_minutes_per_day():
    result = parse_meeting_minutes(SAMPLE_ICS)
    assert result["2026-02-10"] == 75.0
    assert result["2026-02-11"] == 60.0


def test_event_content_is_never_returned():
    """Titles, attendees and locations are parsed past and discarded."""
    result = parse_meeting_minutes(SAMPLE_ICS)
    serialized = str(result)
    for content in ("Confidential", "board", "someone@example.com", "Room 3", "Standup"):
        assert content not in serialized


def test_malformed_events_are_skipped():
    malformed = "BEGIN:VEVENT\nDTSTART:garbage\nDTEND:also-garbage\nEND:VEVENT\n"
    assert parse_meeting_minutes(malformed) == {}


def test_zero_length_event_is_ignored():
    zero = "BEGIN:VEVENT\nDTSTART:20260210T090000Z\nDTEND:20260210T090000Z\nEND:VEVENT\n"
    assert parse_meeting_minutes(zero) == {}


def test_ics_connector_reads_a_file(tmp_path):
    ics_file = tmp_path / "calendar.ics"
    ics_file.write_text(SAMPLE_ICS)

    connector = IcsCalendarConnector()
    features = connector.fetch_daily_features(
        {"ics_path_or_url": str(ics_file)}, "emp1", date(2026, 2, 10), date(2026, 2, 11)
    )

    assert features["2026-02-10"] == {"meeting_minutes": 75.0}
    assert features["2026-02-11"] == {"meeting_minutes": 60.0}


def test_ics_connector_respects_requested_range(tmp_path):
    ics_file = tmp_path / "calendar.ics"
    ics_file.write_text(SAMPLE_ICS)

    connector = IcsCalendarConnector()
    features = connector.fetch_daily_features(
        {"ics_path_or_url": str(ics_file)}, "emp1", date(2026, 2, 11), date(2026, 2, 11)
    )

    assert list(features) == ["2026-02-11"]


def test_unconfigured_connector_raises():
    connector = IcsCalendarConnector()
    assert connector.is_configured({}) is False
    with pytest.raises(ConnectorNotConfigured):
        connector.fetch_daily_features({}, "emp1", date(2026, 2, 10), date(2026, 2, 11))


def test_oauth_connectors_are_declared_but_fail_loudly():
    """An unimplemented connector must raise rather than quietly return
    nothing, so a half-configured integration is never mistaken for a quiet
    one."""
    connector = get_connector("microsoft_graph")
    assert connector is not None
    assert connector.metadata.implemented is False

    with pytest.raises(ConnectorNotConfigured):
        connector.fetch_daily_features({}, "emp1", date(2026, 2, 10), date(2026, 2, 11))


def test_registry_lists_implementation_status():
    by_key = {c["key"]: c for c in available_connectors()}

    assert by_key["ics_calendar"]["implemented"] is True
    assert by_key["ics_calendar"]["auth_kind"] == "none"
    assert by_key["slack"]["implemented"] is False
    assert by_key["slack"]["auth_kind"] == "oauth2"


def test_every_connector_declares_a_consent_source():
    """A connector without a consent gate could supply a signal the employee
    switched off."""
    for connector in available_connectors():
        assert connector["consent_source"]
