from integrations.base import WorkloadConnector
from integrations.google_calendar import GoogleCalendarConnector
from integrations.ics_calendar import IcsCalendarConnector
from integrations.oauth_connectors import DECLARED, UnimplementedConnector

_REGISTRY: dict[str, WorkloadConnector] = {}


def register_connector(connector: WorkloadConnector) -> None:
    _REGISTRY[connector.metadata.key] = connector


def get_connector(key: str) -> WorkloadConnector | None:
    return _REGISTRY.get(key)


def available_connectors() -> list[dict]:
    return [
        {
            "key": c.metadata.key,
            "label": c.metadata.label,
            "consent_source": c.metadata.consent_source,
            "auth_kind": c.metadata.auth_kind,
            "required_config": c.metadata.required_config,
            "implemented": c.metadata.implemented,
            "notes": c.metadata.notes,
        }
        for c in sorted(_REGISTRY.values(), key=lambda c: c.metadata.key)
    ]


register_connector(IcsCalendarConnector())
register_connector(GoogleCalendarConnector())
for metadata in DECLARED:
    register_connector(UnimplementedConnector(metadata))
