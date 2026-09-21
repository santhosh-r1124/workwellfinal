import re

from shared.enums.safety import SafetySeverity

# Deterministic keyword/pattern matching, not an LLM call: safety-critical
# detection must not depend on model availability or be subject to prompt
# injection from the conversation it is scanning (Phase 10).
CRISIS_PATTERNS = [
    r"\bkill myself\b",
    r"\bsuicid\w*\b",
    r"\bend my life\b",
    r"\bwant to die\b",
    r"\bself[- ]harm\w*\b",
    r"\bhurt myself\b",
    r"\bno reason to live\b",
]

CONCERN_PATTERNS = [
    r"\bhopeless\b",
    r"\bcan.?t go on\b",
    r"\bgiven up\b",
    r"\bworthless\b",
    r"\bcan.?t take it anymore\b",
]


def classify(text: str) -> dict:
    lowered = text.lower()

    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, lowered):
            return {"severity": SafetySeverity.CRISIS.value, "category": "explicit_crisis_statement"}

    for pattern in CONCERN_PATTERNS:
        if re.search(pattern, lowered):
            return {"severity": SafetySeverity.CONCERN.value, "category": "distress_statement"}

    return {"severity": SafetySeverity.NONE.value, "category": None}
