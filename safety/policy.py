from shared.enums.safety import SafetySeverity

RESPONSE_BY_SEVERITY = {
    SafetySeverity.CRISIS.value: (
        "It sounds like you might be going through something really difficult right now. You "
        "don't have to handle this alone. If you are in immediate danger, please contact your "
        "local emergency number. In the US you can call or text 988 (Suicide & Crisis Lifeline), "
        "available 24/7. If your employer offers an Employee Assistance Program, it offers free, "
        "confidential support as well."
    ),
    SafetySeverity.CONCERN.value: (
        "That sounds really hard to carry. I'm not able to provide clinical support, but you "
        "don't have to figure this out alone - your organization's Employee Assistance Program "
        "(if available) or a counselor can help. Would it help if I shared some immediate "
        "resources?"
    ),
}

ACTION_BY_SEVERITY = {
    SafetySeverity.CRISIS.value: "crisis_resources_shown",
    SafetySeverity.CONCERN.value: "support_resources_offered",
}


def response_for(severity: str) -> str | None:
    return RESPONSE_BY_SEVERITY.get(severity)


def action_for(severity: str) -> str:
    return ACTION_BY_SEVERITY.get(severity, "none")
