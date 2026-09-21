"""OAuth-gated vendor connectors (Phase 13).

These are declared, not implemented. Each one needs an app registration and
an admin-consented OAuth 2.0 scope grant in the customer's tenant, so there
is nothing that can be meaningfully built or tested here without those
credentials. Declaring them keeps the registry honest - `implemented=False`
surfaces in the admin panel as "requires setup" instead of appearing to work
and silently returning nothing.

Each entry records the minimum scope it would need, so the privacy review of
an integration can happen before anybody writes the client.
"""

from datetime import date

from integrations.base import ConnectorMetadata, ConnectorNotConfigured

MICROSOFT_GRAPH = ConnectorMetadata(
    key="microsoft_graph",
    label="Microsoft 365 Calendar",
    consent_source="calendar_metadata",
    required_config=["tenant_id", "client_id", "client_secret"],
    auth_kind="oauth2",
    implemented=False,
    notes="Needs Calendars.Read (application or delegated). Would return meeting count/duration only.",
)

SLACK = ConnectorMetadata(
    key="slack",
    label="Slack",
    consent_source="application_categories",
    required_config=["client_id", "client_secret"],
    auth_kind="oauth2",
    implemented=False,
    notes=(
        "Would use conversations.history metadata for volume/timing only - never message text, "
        "which is a never-collectible source in this product."
    ),
)

JIRA = ConnectorMetadata(
    key="jira",
    label="Jira",
    consent_source="calendar_metadata",
    required_config=["site_url", "client_id", "client_secret"],
    auth_kind="oauth2",
    implemented=False,
    notes="Would return task counts, deadline density and rework counts - never issue content.",
)

GITHUB = ConnectorMetadata(
    key="github",
    label="GitHub",
    consent_source="application_categories",
    required_config=["app_id", "installation_id", "private_key"],
    auth_kind="oauth2",
    implemented=False,
    notes="Would return commit/PR/review counts and their timestamps - never diff content.",
)

DECLARED = [MICROSOFT_GRAPH, SLACK, JIRA, GITHUB]


class UnimplementedConnector:
    """Fails loudly rather than returning empty data, so a half-configured
    integration can never be mistaken for a quiet one."""

    def __init__(self, metadata: ConnectorMetadata) -> None:
        self.metadata = metadata

    def is_configured(self, config: dict) -> bool:
        return False

    def fetch_daily_features(
        self, config: dict, employee_ref: str, start: date, end: date
    ) -> dict[str, dict]:
        raise ConnectorNotConfigured(
            f"{self.metadata.label} is declared but not implemented: it requires "
            f"{self.metadata.auth_kind} setup ({', '.join(self.metadata.required_config)})."
        )
