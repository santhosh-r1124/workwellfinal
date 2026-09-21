from ml.evaluation.dataset import generate_dataset
from ml.evaluation.detectors import evidence_to_score, persistence_predictions
from ml.evaluation.harness import run_comparison
from ml.evaluation.labels import (
    episodes,
    strain_label,
    sustained_label_series,
)
from ml.evaluation.metrics import calibration_metrics, classification_metrics, detection_latency


def test_strain_label_requires_stress_and_depletion():
    assert strain_label({"stress": 5, "energy": 1, "recovery": 2}) == 1
    # High stress but resources intact: busy-but-coping is not strain.
    assert strain_label({"stress": 5, "energy": 4, "recovery": 4}) == 0
    # Depleted but not stressed.
    assert strain_label({"stress": 2, "energy": 1, "recovery": 1}) == 0
    assert strain_label(None) is None
    assert strain_label({"stress": None, "energy": 1, "recovery": 1}) is None


def test_episodes_finds_contiguous_runs():
    assert episodes([0, 1, 1, 0, 1, 1, 1]) == [(1, 2), (4, 6)]
    assert episodes([0, 0]) == []
    assert episodes([1, 1]) == [(0, 1)]


def test_sustained_label_smooths_single_day_noise():
    days = [{"self_report_stress": 2, "self_report_energy": 4, "self_report_recovery": 4}] * 10
    # One isolated bad day should not become a sustained-strain label.
    days[5] = {"self_report_stress": 5, "self_report_energy": 1, "self_report_recovery": 1}
    labels = sustained_label_series(days)
    assert sum(label for label in labels if label) == 0


def test_sustained_label_keeps_real_episode():
    calm = {"self_report_stress": 2, "self_report_energy": 4, "self_report_recovery": 4}
    strained = {"self_report_stress": 5, "self_report_energy": 1, "self_report_recovery": 1}
    days = [calm] * 5 + [strained] * 8 + [calm] * 5
    labels = sustained_label_series(days)
    assert sum(label for label in labels if label) >= 6


def test_evidence_score_rises_with_persistence():
    weak = evidence_to_score(4.0, max_run=1)
    strong = evidence_to_score(4.0, max_run=5)
    assert strong > weak


def test_persistence_predictions_need_the_full_run():
    scores = [0.9] * 6
    assert persistence_predictions(scores, [1, 2, 3, 4, 5, 6]) == [0, 0, 0, 0, 1, 1]


def test_classification_metrics_basic():
    result = classification_metrics([1, 1, 0, 0], [1, 0, 0, 0])
    assert result["precision"] == 1.0
    assert result["recall"] == 0.5
    assert result["false_positive_rate"] == 0.0


def test_detection_latency_counts_missed_episodes_separately():
    labels = [0, 1, 1, 1, 0, 1, 1]
    predictions = [0, 0, 1, 1, 0, 0, 0]
    result = detection_latency(labels, predictions)
    assert result["episodes"] == 2
    assert result["episodes_detected"] == 1
    assert result["episodes_missed"] == 1
    assert result["median_latency_days"] == 1.0


def test_calibration_metrics_reward_confident_correctness():
    confident_correct = calibration_metrics([1, 1, 0, 0], [0.95, 0.9, 0.05, 0.1])
    confident_wrong = calibration_metrics([1, 1, 0, 0], [0.05, 0.1, 0.95, 0.9])
    assert confident_correct["brier"] < confident_wrong["brier"]


def test_personalized_detector_beats_population_on_synthetic_cohort():
    """The headline Phase 18 claim, asserted rather than just printed."""
    dataset = generate_dataset(employees_per_archetype=3, total_days=45, seed=11)
    result = run_comparison(dataset)

    personalized = result["overall"]["personalized"]
    matched = result["overall"]["population_matched_rate"]

    assert personalized["f1"] > matched["f1"]
    assert personalized["auroc"] > matched["auroc"]
    assert personalized["latency"]["episodes_detected"] > matched["latency"]["episodes_detected"]


def test_population_model_misfires_on_stable_high_workload_employees():
    """The specific failure mode personal baselines exist to prevent: an
    employee whose workload is simply high, and stable, gets flagged by a
    cohort-relative model despite never being strained."""
    dataset = generate_dataset(employees_per_archetype=3, total_days=45, seed=11)
    result = run_comparison(dataset)

    stable_high = result["by_archetype"]["high_baseline_stable"]
    assert stable_high["personalized"]["false_positive_rate"] == 0.0
    assert stable_high["population_matched_rate"]["false_positive_rate"] > 0.5
