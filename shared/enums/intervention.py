from enum import Enum


class InterventionType(str, Enum):
    FOCUS_BLOCK = "focus_block"
    SHUTDOWN_REMINDER = "shutdown_reminder"
    RECOVERY_BREAK = "recovery_break"
    WORKPLACE_SUPPORT_OFFER = "workplace_support_offer"
    NO_ACTION = "no_action"


class InterventionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    SNOOZED = "snoozed"
