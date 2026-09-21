"""Personalized vs population detectors (Phase 18).

Both use identical statistics, the same signal set, the same threshold, and
the same persistence rule. The *only* difference is what each considers
"normal": the employee's own history, or the whole cohort pooled. That
isolates the variable the comparison is actually about.

Both also apply the product's persistence requirement (a signal must be
anomalous for PERSISTENCE_MIN_DAYS consecutive days before the detector
fires). Evaluating a single-day trigger instead would be measuring a
detector this product does not ship: it would inflate recall, report a
latency of zero, and wreck precision on ordinary day-to-day noise.
"""

import math

from ml.anomaly.zscore import ANOMALY_Z_THRESHOLD, is_anomalous, robust_zscore
from ml.baseline.baseline_engine import compute_baseline
from shared.constants.wellbeing import (
    BASELINE_MIN_DAYS,
    PERSISTENCE_MIN_DAYS,
    TRACKED_PATTERN_SIGNALS,
)

SIGNAL_FIELDS = list(TRACKED_PATTERN_SIGNALS.values())


def _squash(max_abs_z: float, threshold: float = ANOMALY_Z_THRESHOLD) -> float:
    return 1 / (1 + math.exp(-(max_abs_z - threshold)))


def evidence_to_score(max_abs_z: float, max_run: int) -> float:
    """Continuous evidence combining deviation size with how long it has
    persisted. Monotone in both, which is what the product actually acts on.
    Uncalibrated by design - calibration metrics therefore grade this mapping
    alongside the detector, which is the honest framing."""
    persistence_weight = min(1.0, max_run / PERSISTENCE_MIN_DAYS)
    return _squash(max_abs_z) * persistence_weight


def _accumulate(
    per_day_flags: list[dict[str, bool]], per_day_max_z: list[float]
) -> tuple[list[float], list[int]]:
    """Turn per-signal daily anomaly flags into, for each day, the longest
    consecutive anomalous run across any single signal ending that day."""
    runs: dict[str, int] = {}
    max_runs = []

    for flags in per_day_flags:
        longest = 0
        for field in SIGNAL_FIELDS:
            if flags.get(field):
                runs[field] = runs.get(field, 0) + 1
            else:
                runs[field] = 0
            longest = max(longest, runs[field])
        max_runs.append(longest)

    return per_day_max_z, max_runs


def personalized_evidence(
    employee_days: list[dict], z_threshold: float = ANOMALY_Z_THRESHOLD
) -> tuple[list[float | None], list[int]]:
    """Scores each day against that employee's own prior history, causally -
    never using a future day to judge the present."""
    per_day_flags: list[dict[str, bool]] = []
    per_day_max_z: list[float] = []

    for i in range(len(employee_days)):
        flags: dict[str, bool] = {}
        max_abs_z = 0.0

        if i >= BASELINE_MIN_DAYS:
            for field in SIGNAL_FIELDS:
                history = [
                    employee_days[j].get(field)
                    for j in range(i)
                    if employee_days[j].get(field) is not None
                ]
                current = employee_days[i].get(field)
                if current is None or len(history) < BASELINE_MIN_DAYS:
                    continue
                z = robust_zscore(current, compute_baseline(history))
                flags[field] = is_anomalous(z, z_threshold)
                max_abs_z = max(max_abs_z, abs(z))

        per_day_flags.append(flags)
        per_day_max_z.append(max_abs_z)

    z_values, runs = _accumulate(per_day_flags, per_day_max_z)
    scores: list[float | None] = [
        None if i < BASELINE_MIN_DAYS else evidence_to_score(z_values[i], runs[i])
        for i in range(len(employee_days))
    ]
    return scores, runs


def population_baselines(all_employee_days: dict[str, list[dict]]) -> dict[str, dict]:
    """One baseline per signal, pooled across every employee in the cohort."""
    return {
        field: compute_baseline(
            [
                day.get(field)
                for days in all_employee_days.values()
                for day in days
                if day.get(field) is not None
            ]
        )
        for field in SIGNAL_FIELDS
    }


def population_evidence(
    employee_days: list[dict],
    baselines: dict[str, dict],
    z_threshold: float = ANOMALY_Z_THRESHOLD,
) -> tuple[list[float | None], list[int]]:
    """Same machinery against a cohort-wide norm. Given the same warm-up gap
    as the personalized detector so both are scored over identical days.

    z_threshold is tunable so the population detector can also be evaluated
    at a matched alert rate - otherwise it simply never fires against a
    pooled baseline whose spread is inflated by cohort heterogeneity, and
    'it never fires' is a weaker claim than 'it fires on the wrong people'.
    """
    per_day_flags: list[dict[str, bool]] = []
    per_day_max_z: list[float] = []

    for i in range(len(employee_days)):
        flags: dict[str, bool] = {}
        max_abs_z = 0.0

        if i >= BASELINE_MIN_DAYS:
            for field in SIGNAL_FIELDS:
                current = employee_days[i].get(field)
                if current is None:
                    continue
                z = robust_zscore(current, baselines[field])
                flags[field] = is_anomalous(z, z_threshold)
                max_abs_z = max(max_abs_z, abs(z))

        per_day_flags.append(flags)
        per_day_max_z.append(max_abs_z)

    z_values, runs = _accumulate(per_day_flags, per_day_max_z)
    scores: list[float | None] = [
        None if i < BASELINE_MIN_DAYS else evidence_to_score(z_values[i], runs[i])
        for i in range(len(employee_days))
    ]
    return scores, runs


def persistence_predictions(
    scores: list[float | None], runs: list[int], min_days: int = PERSISTENCE_MIN_DAYS
) -> list[int | None]:
    """The product's actual decision rule: fire only once a signal has been
    anomalous for min_days consecutive days."""
    return [None if score is None else int(runs[i] >= min_days) for i, score in enumerate(scores)]
