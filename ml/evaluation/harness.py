"""Runs a dataset through both detectors and compares them (Phase 18).

Three columns are reported:

  personalized              - the shipped detector, own-history baseline
  population                - same machinery, cohort-pooled baseline, same
                              z-threshold
  population_matched_rate   - cohort-pooled baseline with its z-threshold
                              tuned so it raises roughly as many alerts as
                              the personalized detector

The third column exists because a pooled baseline inflated by cohort
heterogeneity tends not to fire at all at the default threshold, and "it
never fires" is both a weak claim and easy to dismiss as a rigged
comparison. Forcing it to alert at a comparable rate asks the sharper
question: when it does fire, does it fire on the right people?
"""

from ml.anomaly.zscore import ANOMALY_Z_THRESHOLD
from ml.evaluation.detectors import (
    persistence_predictions,
    personalized_evidence,
    population_baselines,
    population_evidence,
)
from ml.evaluation.labels import sustained_label_series
from ml.evaluation.metrics import evaluate

DETECTORS = ("personalized", "population", "population_matched_rate")
CANDIDATE_Z_THRESHOLDS = [round(0.25 * i, 2) for i in range(2, 25)]


def _empty_bucket() -> dict:
    return {name: {"labels": [], "scores": [], "predictions": []} for name in DETECTORS}


def _alert_rate(predictions: list[int | None]) -> float:
    fired = [p for p in predictions if p is not None]
    return sum(fired) / len(fired) if fired else 0.0


def _population_alert_rate(
    dataset: dict[str, list[dict]], baselines: dict, z_threshold: float
) -> float:
    total, fired = 0, 0
    for days in dataset.values():
        scores, runs = population_evidence(days, baselines, z_threshold)
        predictions = persistence_predictions(scores, runs)
        present = [p for p in predictions if p is not None]
        total += len(present)
        fired += sum(present)
    return fired / total if total else 0.0


def _matched_z_threshold(
    dataset: dict[str, list[dict]], baselines: dict, target_rate: float
) -> float:
    best_threshold = ANOMALY_Z_THRESHOLD
    best_gap = float("inf")
    for candidate in CANDIDATE_Z_THRESHOLDS:
        rate = _population_alert_rate(dataset, baselines, candidate)
        gap = abs(rate - target_rate)
        if gap < best_gap:
            best_gap, best_threshold = gap, candidate
    return best_threshold


def run_comparison(dataset: dict[str, list[dict]]) -> dict:
    baselines = population_baselines(dataset)

    # Personalized detector first, so its alert rate can set the target the
    # population detector is matched against.
    personalized_cache = {}
    personalized_predictions: list[int | None] = []
    for employee_id, days in dataset.items():
        scores, runs = personalized_evidence(days)
        predictions = persistence_predictions(scores, runs)
        personalized_cache[employee_id] = (scores, runs, predictions)
        personalized_predictions.extend(predictions)

    target_rate = _alert_rate(personalized_predictions)
    matched_threshold = _matched_z_threshold(dataset, baselines, target_rate)

    pooled = _empty_bucket()
    per_archetype: dict[str, dict] = {}

    for employee_id, days in dataset.items():
        if not days:
            continue

        labels = sustained_label_series(days)
        archetype = days[0].get("archetype", "unknown")
        archetype_bucket = per_archetype.setdefault(archetype, _empty_bucket())

        personal_scores, _, personal_predictions = personalized_cache[employee_id]
        pop_scores, pop_runs = population_evidence(days, baselines)
        matched_scores, matched_runs = population_evidence(days, baselines, matched_threshold)

        outputs = {
            "personalized": (personal_scores, personal_predictions),
            "population": (pop_scores, persistence_predictions(pop_scores, pop_runs)),
            "population_matched_rate": (
                matched_scores,
                persistence_predictions(matched_scores, matched_runs),
            ),
        }

        for name, (scores, predictions) in outputs.items():
            for target in (pooled[name], archetype_bucket[name]):
                target["labels"].extend(labels)
                target["scores"].extend(scores)
                target["predictions"].extend(predictions)

    return {
        "employees": len(dataset),
        "personalized_alert_rate": round(target_rate, 4),
        "matched_population_z_threshold": matched_threshold,
        "overall": {
            name: evaluate(data["labels"], data["scores"], data["predictions"])
            for name, data in pooled.items()
        },
        "by_archetype": {
            archetype: {
                name: evaluate(data["labels"], data["scores"], data["predictions"])
                for name, data in detectors.items()
            }
            for archetype, detectors in per_archetype.items()
        },
    }
