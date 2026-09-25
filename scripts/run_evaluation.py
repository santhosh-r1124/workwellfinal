"""Compares the personalized detector against population-baseline detectors
(Phases 17-18) and prints a report.

    python scripts/run_evaluation.py [--json out.json]

Caveat, stated up front because it governs how the numbers should be read:
this runs on synthetic data, so it measures whether the detector recovers a
known generative signal. It is not evidence of real-world clinical validity,
which would require consented longitudinal data and validated instruments.
"""

import sys
from pathlib import Path

# So `python scripts/...` works from a clean shell, without the caller
# having to know to export PYTHONPATH. The container sets it; a developer
# following the README from a fresh terminal does not.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json

from ml.evaluation.dataset import generate_dataset
from ml.evaluation.harness import run_comparison

COLUMNS = [
    ("personalized", "Personalized"),
    ("population", "Population"),
    ("population_matched_rate", "Pop (matched)"),
]

METRIC_ROWS = [
    ("precision", "Precision"),
    ("recall", "Recall"),
    ("f1", "F1"),
    ("false_positive_rate", "False positive rate"),
    ("auroc", "AUROC"),
    ("auprc", "AUPRC"),
    ("brier", "Brier (lower better)"),
    ("ece", "Calibration error (lower better)"),
]

LABEL_WIDTH = 30
COL_WIDTH = 15


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _header(title: str) -> None:
    print(f"\n{title:<{LABEL_WIDTH}}" + "".join(f"{label:>{COL_WIDTH}}" for _, label in COLUMNS))
    print("-" * (LABEL_WIDTH + COL_WIDTH * len(COLUMNS)))


def print_report(result: dict) -> None:
    print("=" * (LABEL_WIDTH + COL_WIDTH * len(COLUMNS)))
    print("WorkWell AI - personalized vs population baseline detection")
    print("=" * (LABEL_WIDTH + COL_WIDTH * len(COLUMNS)))
    print(f"Employees: {result['employees']}")
    print("Both detectors apply the product's persistence rule (5 consecutive days).")
    print(
        f"Personalized alert rate {result['personalized_alert_rate']:.3f}; population detector "
        f"matched at z={result['matched_population_z_threshold']}."
    )
    print("Synthetic data: measures recovery of a known signal, not clinical validity.")

    overall = result["overall"]
    print(
        f"\nEvaluated days: {overall['personalized']['evaluated_days']}  "
        f"(positive rate {overall['personalized']['positive_rate']:.3f})"
    )

    _header("Metric")
    for key, label in METRIC_ROWS:
        row = "".join(f"{_fmt(overall[name].get(key)):>{COL_WIDTH}}" for name, _ in COLUMNS)
        print(f"{label:<{LABEL_WIDTH}}{row}")

    _header("Detection latency")
    detected_cells = []
    for name, _ in COLUMNS:
        latency = overall[name]["latency"]
        cell = f"{latency['episodes_detected']}/{latency['episodes']}"
        detected_cells.append(f"{cell:>{COL_WIDTH}}")
    print(f"{'Episodes detected':<{LABEL_WIDTH}}{''.join(detected_cells)}")
    median = "".join(
        f"{_fmt(overall[name]['latency']['median_latency_days']):>{COL_WIDTH}}" for name, _ in COLUMNS
    )
    print(f"{'Median latency (days)':<{LABEL_WIDTH}}{median}")

    _header("False positive rate by archetype")
    for archetype, detectors in sorted(result["by_archetype"].items()):
        row = "".join(
            f"{_fmt(detectors[name].get('false_positive_rate')):>{COL_WIDTH}}" for name, _ in COLUMNS
        )
        print(f"{archetype:<{LABEL_WIDTH}}{row}")

    _header("Recall by archetype (strained only)")
    for archetype, detectors in sorted(result["by_archetype"].items()):
        if not detectors["personalized"].get("positive_rate"):
            continue  # no strain in this archetype, recall is undefined
        row = "".join(f"{_fmt(detectors[name].get('recall')):>{COL_WIDTH}}" for name, _ in COLUMNS)
        print(f"{archetype:<{LABEL_WIDTH}}{row}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--employees-per-archetype", type=int, default=6)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--json", type=str, default=None, help="write full results to this path")
    args = parser.parse_args()

    dataset = generate_dataset(
        employees_per_archetype=args.employees_per_archetype,
        total_days=args.days,
        seed=args.seed,
    )
    result = run_comparison(dataset)
    print_report(result)

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(result, fh, indent=2)
        print(f"Full results written to {args.json}")


if __name__ == "__main__":
    main()
