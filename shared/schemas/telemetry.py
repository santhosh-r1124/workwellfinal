from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DesktopFeatures(BaseModel):
    """Aggregated, privacy-preserving features emitted by the desktop agent.

    Raw input (keystrokes, window titles, etc.) never appears here - the
    desktop agent discards it immediately after computing these aggregates.
    """

    active_minutes: float | None = None
    idle_minutes: float | None = None
    break_minutes: float | None = None
    continuous_session_minutes: float | None = None

    application_switch_count: int | None = None
    context_switches: int | None = None

    typing_speed: float | None = None
    inter_key_interval: float | None = None
    pause_rate: float | None = None
    backspace_rate: float | None = None
    correction_rate: float | None = None
    typing_burst_length: float | None = None

    meeting_minutes: float | None = None

    model_config = ConfigDict(extra="forbid")


class TelemetryEventIn(BaseModel):
    employee_id: str
    timestamp: datetime
    features: DesktopFeatures

    model_config = ConfigDict(extra="forbid")


class SelfReportIn(BaseModel):
    employee_id: str
    date: str
    stress: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    recovery: int = Field(ge=1, le=5)
    note: str | None = None
