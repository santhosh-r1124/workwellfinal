"""ICS calendar connector (Phase 13).

Fully implemented and testable because ICS needs no OAuth: most calendar
products expose a private subscribe URL or an exported .ics file. Only
start/end times are read - summaries, attendees, locations and descriptions
are parsed past and discarded, so what leaves this module is meeting minutes
per day and nothing else.
"""

from datetime import date, datetime, timedelta

from integrations.base import ConnectorMetadata, require_config
from integrations.url_guard import fetch_text

METADATA = ConnectorMetadata(
    key="ics_calendar",
    label="Calendar (ICS)",
    consent_source="calendar_metadata",
    required_config=["ics_path_or_url"],
    auth_kind="none",
    implemented=True,
    notes="Reads a .ics export or private subscribe URL. Times only, never event content.",
)


def _parse_ics_datetime(value: str) -> datetime | None:
    value = value.strip()
    # Strip any parameters already handled by the caller; handle UTC 'Z' and
    # naive local forms, plus all-day DATE values.
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_meeting_minutes(ics_text: str) -> dict[str, float]:
    """Returns {iso_date: meeting_minutes}. Events spanning midnight are
    attributed to the day they start, which keeps the daily feature aligned
    with how the desktop agent reports."""
    per_day: dict[str, float] = {}
    start: datetime | None = None
    end: datetime | None = None
    in_event = False

    for raw_line in ics_text.splitlines():
        line = raw_line.strip()

        if line == "BEGIN:VEVENT":
            in_event, start, end = True, None, None
            continue
        if line == "END:VEVENT":
            if start and end and end > start:
                minutes = (end - start).total_seconds() / 60
                key = start.date().isoformat()
                per_day[key] = round(per_day.get(key, 0.0) + minutes, 1)
            in_event, start, end = False, None, None
            continue
        if not in_event or ":" not in line:
            continue

        name, _, value = line.partition(":")
        field = name.split(";")[0].upper()
        if field == "DTSTART":
            start = _parse_ics_datetime(value)
        elif field == "DTEND":
            end = _parse_ics_datetime(value)

    return per_day


class IcsCalendarConnector:
    metadata = METADATA

    def is_configured(self, config: dict) -> bool:
        return bool(config.get("ics_path_or_url"))

    def fetch_daily_features(
        self, config: dict, employee_ref: str, start: date, end: date
    ) -> dict[str, dict]:
        require_config(METADATA, config)
        source = config["ics_path_or_url"]

        if source.startswith("http://") or source.startswith("https://"):
            # The employee chose this URL, so the server must not simply
            # go where it is told - see integrations/url_guard.py.
            ics_text = fetch_text(source)
        else:
            with open(source, encoding="utf-8", errors="replace") as fh:
                ics_text = fh.read()

        per_day = parse_meeting_minutes(ics_text)

        features: dict[str, dict] = {}
        cursor = start
        while cursor <= end:
            key = cursor.isoformat()
            if key in per_day:
                features[key] = {"meeting_minutes": per_day[key]}
            cursor += timedelta(days=1)
        return features
