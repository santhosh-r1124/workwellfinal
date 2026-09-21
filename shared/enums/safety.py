from enum import Enum


class SafetySeverity(str, Enum):
    NONE = "none"
    WATCH = "watch"
    CONCERN = "concern"
    CRISIS = "crisis"
