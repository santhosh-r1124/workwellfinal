class ConsentGate:
    """Local mirror of the employee's consent settings. Collectors consult
    this before even starting to gather a signal - disabled signals are
    never computed on-device, not just filtered before upload."""

    def __init__(self, consent: dict) -> None:
        self._consent = consent

    def allows(self, source: str) -> bool:
        return bool(self._consent.get(source, False))
