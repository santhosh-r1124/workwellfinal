# Dashboard-facing labels. WorkWell never surfaces clinical/diagnostic scores.
FORBIDDEN_LABELS = [
    "depression score",
    "anxiety score",
    "mental health score",
    "burnout score",
    "risk score",
]

DASHBOARD_DIMENSIONS = ["workload", "recovery", "focus", "schedule", "communication"]

# Persistence rule (Phase 5.2): a signal must be anomalous for this many
# consecutive days before it contributes to a PERSISTENT_PATTERN.
PERSISTENCE_MIN_DAYS = 5

# A sustained pattern produces the same finding every day it persists, so
# a nudge of a given type is not repeated inside this window. See
# agent_repo.intervention_within_cooldown for why.
INTERVENTION_COOLDOWN_DAYS = 3

# How long a nudge stays on the employee's dashboard. One nobody answered
# a fortnight ago is not a suggestion any more, it is clutter.
INTERVENTION_VISIBLE_DAYS = 14

# Minimum days of history required before a baseline is considered usable.
BASELINE_MIN_DAYS = 7
BASELINE_TARGET_DAYS = 14

# Surfaced in dashboard explainability (Phase 9.2) as a product differentiator.
NEVER_COLLECTED_LABELS = ["Webcam", "Raw keyboard", "Message content", "Call recordings"]

TRACKED_PATTERN_SIGNALS = {
    "after_hours_work": "after_hours",
    "meeting_load": "meeting_load",
    "recovery_gap": "recovery_gap",
    "context_switch_rate": "context_switch_rate",
    "focus_fragmentation": "focus_fragmentation",
    "typing_deviation": "typing_deviation",
}
