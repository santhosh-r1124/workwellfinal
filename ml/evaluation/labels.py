"""Ground-truth labelling for evaluation (Phase 17).

The label comes from what the employee said about themselves, never from the
behavioral signal the detector is being scored on. Deriving the label from
telemetry would make the evaluation circular - the detector would be graded
on reproducing its own input.
"""

STRESS_THRESHOLD = 4  # 1-5 scale, >= is elevated
LOW_RESOURCE_THRESHOLD = 2  # 1-5 scale, <= is depleted


def strain_label(self_report: dict | None) -> int | None:
    """1 = self-reported strain, 0 = not, None = no self-report that day.

    Requires elevated stress AND a depleted resource (energy or recovery).
    Stress alone is a poor label: a busy-but-coping week reports high stress
    without the depletion that matters for early warning.
    """
    if not self_report:
        return None

    stress = self_report.get("stress")
    energy = self_report.get("energy")
    recovery = self_report.get("recovery")

    if stress is None or (energy is None and recovery is None):
        return None

    depleted = (energy is not None and energy <= LOW_RESOURCE_THRESHOLD) or (
        recovery is not None and recovery <= LOW_RESOURCE_THRESHOLD
    )
    return 1 if (stress >= STRESS_THRESHOLD and depleted) else 0


def label_series(days: list[dict]) -> list[int | None]:
    return [
        strain_label(
            {
                "stress": d.get("self_report_stress"),
                "energy": d.get("self_report_energy"),
                "recovery": d.get("self_report_recovery"),
            }
        )
        for d in days
    ]


def sustained_label_series(
    days: list[dict], window: int = 5, min_fraction: float = 0.6
) -> list[int | None]:
    """Smooths the day-level labels into 'is this person in a sustained
    strained state'.

    This is the target the product actually claims to detect - it explicitly
    does not fire on a single bad day - so scoring against raw day-level
    labels would penalise the detector for correctly ignoring one-off noise.

    The window is centred, not trailing: a trailing window would delay label
    onset relative to the true onset and make detection latency look better
    than it is.
    """
    raw = label_series(days)
    half = window // 2
    smoothed: list[int | None] = []

    for i in range(len(raw)):
        lo = max(0, i - half)
        hi = min(len(raw), i + half + 1)
        present = [label for label in raw[lo:hi] if label is not None]
        if not present:
            smoothed.append(None)
            continue
        smoothed.append(int(sum(present) / len(present) >= min_fraction))

    return smoothed


def episodes(labels: list[int | None]) -> list[tuple[int, int]]:
    """Contiguous runs of positive labels, as (start_index, end_index)
    inclusive. Used for detection-latency scoring, where what matters is how
    quickly an episode is caught, not each individual day."""
    runs = []
    start = None
    for i, label in enumerate(labels):
        if label == 1 and start is None:
            start = i
        elif label != 1 and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(labels) - 1))
    return runs
