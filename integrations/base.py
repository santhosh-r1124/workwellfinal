"""Connector interface for enterprise workload sources (Phase 13).

Every connector returns the *same* privacy-preserving shape the desktop
agent produces: counts and durations, never content. A calendar connector
returns meeting minutes, not meeting titles or attendees; an issue-tracker
connector would return task counts, not ticket text. Anything richer would
route around the consent model rather than extend it.

Auth reality check: Microsoft Graph, Slack and Jira all require OAuth 2.0
app registration and delegated/application permissions. They cannot be
reduced to "paste one API key", so connectors declare what they need via
`metadata.required_config` and refuse to run without it rather than
pretending to be configured.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable


class ConnectorNotConfigured(RuntimeError):
    """Raised when a connector is invoked without the credentials it declared."""


@dataclass(frozen=True)
class ConnectorMetadata:
    key: str
    label: str
    # Which consent source gates this connector. A connector must never
    # supply a signal the employee has not consented to.
    consent_source: str
    required_config: list[str] = field(default_factory=list)
    auth_kind: str = "none"  # "none" | "api_key" | "oauth2"
    implemented: bool = True
    notes: str = ""


@runtime_checkable
class WorkloadConnector(Protocol):
    metadata: ConnectorMetadata

    def is_configured(self, config: dict) -> bool: ...

    def fetch_daily_features(
        self, config: dict, employee_ref: str, start: date, end: date
    ) -> dict[str, dict]:
        """Returns {iso_date: {feature_name: value}} using the same feature
        names as shared.schemas.telemetry.DesktopFeatures."""
        ...


def require_config(metadata: ConnectorMetadata, config: dict) -> None:
    missing = [key for key in metadata.required_config if not config.get(key)]
    if missing:
        raise ConnectorNotConfigured(
            f"{metadata.label} is missing required configuration: {', '.join(missing)}"
        )
