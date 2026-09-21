from enum import Enum


class DataSourceKey(str, Enum):
    WORKING_HOURS = "working_hours"
    BREAK_PATTERNS = "break_patterns"
    APPLICATION_CATEGORIES = "application_categories"
    TYPING_DYNAMICS = "typing_dynamics"
    CALENDAR_METADATA = "calendar_metadata"
    WEBCAM = "webcam"
    RAW_KEYBOARD = "raw_keyboard"
    AUDIO_RECORDING = "audio_recording"
    MESSAGE_CONTENT = "message_content"


# Sources that are collected in aggregate/derived form only, on by default,
# and considered low-sensitivity behavioral signals.
DEFAULT_ENABLED_SOURCES = {
    DataSourceKey.WORKING_HOURS,
    DataSourceKey.BREAK_PATTERNS,
    DataSourceKey.APPLICATION_CATEGORIES,
    DataSourceKey.TYPING_DYNAMICS,
}

# Sources that WorkWell never collects in this product, regardless of consent.
# Enforced in code (see shared/constants/privacy.py), not just policy.
PERMANENTLY_DISABLED_SOURCES = {
    DataSourceKey.RAW_KEYBOARD,
    DataSourceKey.WEBCAM,
    DataSourceKey.AUDIO_RECORDING,
    DataSourceKey.MESSAGE_CONTENT,
}
