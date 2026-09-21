from dataclasses import dataclass

from shared.enums.data_sources import DataSourceKey


@dataclass(frozen=True)
class DataSourceDefinition:
    key: DataSourceKey
    label: str
    category: str
    what: str
    why: str
    where: str
    retention: str
    who_can_access: str
    default_enabled: bool
    collectible: bool  # False = product never collects this, regardless of toggle


DATA_SOURCE_CATALOG: list[DataSourceDefinition] = [
    DataSourceDefinition(
        key=DataSourceKey.WORKING_HOURS,
        label="Work hours",
        category="schedule",
        what="Start/end of active work sessions, active vs. idle minutes.",
        why="Establishes your personal baseline schedule and detects overtime/after-hours drift.",
        where="Processed on your device, aggregated features stored in the organization's WorkWell database.",
        retention="90 days of daily aggregates, then summarized to weekly trend only.",
        who_can_access="You, and the automated WorkWell analysis pipeline. Not shared with your manager individually.",
        default_enabled=True,
        collectible=True,
    ),
    DataSourceDefinition(
        key=DataSourceKey.BREAK_PATTERNS,
        label="Break analytics",
        category="recovery",
        what="Count and length of breaks, gaps between active sessions.",
        why="Detects recovery/break debt that precedes burnout.",
        where="Processed on your device, aggregated features stored in the organization's WorkWell database.",
        retention="90 days of daily aggregates, then summarized to weekly trend only.",
        who_can_access="You, and the automated WorkWell analysis pipeline.",
        default_enabled=True,
        collectible=True,
    ),
    DataSourceDefinition(
        key=DataSourceKey.APPLICATION_CATEGORIES,
        label="Application categories",
        category="focus",
        what=(
            "Category of active application (e.g. 'communication', 'code editor', 'meetings') "
            "and switch counts. Never window titles or content."
        ),
        why="Detects context-switching and focus fragmentation.",
        where="Categorized on your device; only category counts leave the device.",
        retention="90 days of daily aggregates.",
        who_can_access="You, and the automated WorkWell analysis pipeline.",
        default_enabled=True,
        collectible=True,
    ),
    DataSourceDefinition(
        key=DataSourceKey.TYPING_DYNAMICS,
        label="Typing dynamics",
        category="focus",
        what=(
            "Aggregate typing speed, pause rate, correction rate, computed per interval. "
            "Never key content."
        ),
        why="Aggregate typing cadence changes correlate with fatigue and cognitive load.",
        where=(
            "Computed on your device from raw keystrokes, which are discarded immediately "
            "after aggregation."
        ),
        retention="90 days of daily aggregates.",
        who_can_access="You, and the automated WorkWell analysis pipeline.",
        default_enabled=True,
        collectible=True,
    ),
    DataSourceDefinition(
        key=DataSourceKey.CALENDAR_METADATA,
        label="Calendar metadata",
        category="workload",
        what="Meeting count and duration (titles/attendees excluded).",
        why="Explains workload spikes with meeting-load context.",
        where="Retrieved via your organization's calendar integration, if connected.",
        retention="90 days.",
        who_can_access="You, and the automated WorkWell analysis pipeline.",
        default_enabled=False,
        collectible=True,
    ),
    DataSourceDefinition(
        key=DataSourceKey.WEBCAM,
        label="Webcam",
        category="never",
        what="Not collected.",
        why="Not applicable.",
        where="Not applicable.",
        retention="Not applicable.",
        who_can_access="Nobody.",
        default_enabled=False,
        collectible=False,
    ),
    DataSourceDefinition(
        key=DataSourceKey.RAW_KEYBOARD,
        label="Raw keyboard",
        category="never",
        what="Not collected.",
        why="Not applicable.",
        where="Not applicable.",
        retention="Not applicable.",
        who_can_access="Nobody.",
        default_enabled=False,
        collectible=False,
    ),
    DataSourceDefinition(
        key=DataSourceKey.AUDIO_RECORDING,
        label="Audio recording",
        category="never",
        what="Not collected.",
        why="Not applicable.",
        where="Not applicable.",
        retention="Not applicable.",
        who_can_access="Nobody.",
        default_enabled=False,
        collectible=False,
    ),
    DataSourceDefinition(
        key=DataSourceKey.MESSAGE_CONTENT,
        label="Message content",
        category="never",
        what="Not collected.",
        why="Not applicable.",
        where="Not applicable.",
        retention="Not applicable.",
        who_can_access="Nobody.",
        default_enabled=False,
        collectible=False,
    ),
]

DATA_SOURCE_BY_KEY = {d.key: d for d in DATA_SOURCE_CATALOG}

# Which raw DesktopFeatures fields each consent toggle gates. A disabled
# source means these fields are stripped from telemetry before it is ever
# written to the database - not filtered at query time.
FIELD_GATES: dict[DataSourceKey, list[str]] = {
    DataSourceKey.WORKING_HOURS: ["active_minutes", "idle_minutes", "continuous_session_minutes"],
    DataSourceKey.BREAK_PATTERNS: ["break_minutes"],
    DataSourceKey.APPLICATION_CATEGORIES: ["application_switch_count", "context_switches"],
    DataSourceKey.TYPING_DYNAMICS: [
        "typing_speed",
        "inter_key_interval",
        "pause_rate",
        "backspace_rate",
        "correction_rate",
        "typing_burst_length",
    ],
    DataSourceKey.CALENDAR_METADATA: ["meeting_minutes"],
}
