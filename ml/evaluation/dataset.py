"""Synthetic evaluation dataset (Phase 17).

A latent per-day "strain" state drives the behavioral signals and the
self-report *independently*, each with its own noise. That matters: if the
label were a deterministic function of the signals, any detector would score
perfectly and the evaluation would measure nothing.

Four archetypes exist specifically to separate personalized from population
detection:

  normal                - never strained, mid-range absolute values
  escalating            - genuine strain episode, mid-range values
  high_baseline_stable  - always-high absolute values, never strained
                          (a population model should false-positive here)
  low_baseline_shift    - genuine strain, but absolute values stay below the
                          cohort median (a population model should miss it)
"""

import random

from ml.evaluation.detectors import SIGNAL_FIELDS

ARCHETYPES = ["normal", "escalating", "high_baseline_stable", "low_baseline_shift"]

BASELINE_LEVEL = {
    "normal": 1.0,
    "escalating": 1.0,
    "high_baseline_stable": 2.6,
    "low_baseline_shift": 0.4,
}

# Multiplicative bump applied to every tracked signal while strained.
STRAIN_EFFECT = 0.9
SIGNAL_NOISE = 0.08


def _strain_days(archetype: str, total_days: int, rng: random.Random) -> set[int]:
    if archetype in ("normal", "high_baseline_stable"):
        return set()
    onset = rng.randint(total_days // 2, total_days - 12)
    return set(range(onset, total_days))


def _self_report(strained: bool, rng: random.Random) -> dict:
    """Noisy: a strained person sometimes reports an okay day and vice
    versa, so the label is correlated with - not identical to - the latent
    state."""
    if strained:
        return {
            "self_report_stress": min(5, max(1, round(rng.gauss(4.3, 0.7)))),
            "self_report_energy": min(5, max(1, round(rng.gauss(1.8, 0.7)))),
            "self_report_recovery": min(5, max(1, round(rng.gauss(1.9, 0.7)))),
        }
    return {
        "self_report_stress": min(5, max(1, round(rng.gauss(2.4, 0.7)))),
        "self_report_energy": min(5, max(1, round(rng.gauss(3.7, 0.7)))),
        "self_report_recovery": min(5, max(1, round(rng.gauss(3.6, 0.7)))),
    }


def generate_employee(
    archetype: str, total_days: int, rng: random.Random
) -> list[dict]:
    level = BASELINE_LEVEL[archetype]
    strained_days = _strain_days(archetype, total_days, rng)

    days = []
    for day_index in range(total_days):
        strained = day_index in strained_days
        day: dict = {"day_index": day_index, "archetype": archetype, "strained": strained}

        for field in SIGNAL_FIELDS:
            base = level * (1 + STRAIN_EFFECT if strained else 1.0)
            day[field] = round(max(0.0, base * (1 + rng.gauss(0, SIGNAL_NOISE))), 4)

        day.update(_self_report(strained, rng))
        days.append(day)

    return days


def generate_dataset(
    employees_per_archetype: int = 6, total_days: int = 60, seed: int = 7
) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    dataset: dict[str, list[dict]] = {}
    for archetype in ARCHETYPES:
        for i in range(employees_per_archetype):
            dataset[f"{archetype}_{i}"] = generate_employee(archetype, total_days, rng)
    return dataset
