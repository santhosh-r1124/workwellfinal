"""Evaluation metrics (Phase 18)."""

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from ml.evaluation.labels import episodes


def _confusion(y_true: list[int], y_pred: list[int]) -> tuple[int, int, int, int]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    return tp, fp, fn, tn


def classification_metrics(y_true: list[int], y_pred: list[int]) -> dict:
    tp, fp, fn, tn = _confusion(y_true, y_pred)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
    }


def ranking_metrics(y_true: list[int], y_score: list[float]) -> dict:
    # AUROC/AUPRC are undefined with a single class present.
    if len(set(y_true)) < 2:
        return {"auroc": None, "auprc": None}
    return {
        "auroc": round(float(roc_auc_score(y_true, y_score)), 4),
        "auprc": round(float(average_precision_score(y_true, y_score)), 4),
    }


def calibration_metrics(y_true: list[int], y_score: list[float], bins: int = 10) -> dict:
    """Brier score plus expected calibration error. Both measure the
    score->probability mapping as much as the detector itself (see
    detectors._score_from_z), so they are useful for comparing the two
    detectors against each other, not as absolute probability quality."""
    true_arr = np.array(y_true, dtype=float)
    score_arr = np.array(y_score, dtype=float)

    brier = float(np.mean((score_arr - true_arr) ** 2))

    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for i in range(bins):
        lower, upper = edges[i], edges[i + 1]
        mask = (score_arr > lower) & (score_arr <= upper) if i > 0 else (score_arr <= upper)
        if not mask.any():
            continue
        bin_confidence = float(score_arr[mask].mean())
        bin_accuracy = float(true_arr[mask].mean())
        ece += (mask.sum() / len(score_arr)) * abs(bin_confidence - bin_accuracy)

    return {"brier": round(brier, 4), "ece": round(float(ece), 4)}


def detection_latency(labels: list[int | None], predictions: list[int | None]) -> dict:
    """Per strain episode, how many days from onset until the detector first
    fires. Episodes never caught are counted separately rather than being
    folded in as a large number, which would quietly flatter a detector that
    misses episodes entirely."""
    latencies = []
    missed = 0

    for start, end in episodes(labels):
        fired_at = None
        for i in range(start, end + 1):
            if i < len(predictions) and predictions[i] == 1:
                fired_at = i
                break
        if fired_at is None:
            missed += 1
        else:
            latencies.append(fired_at - start)

    return {
        "episodes": len(episodes(labels)),
        "episodes_detected": len(latencies),
        "episodes_missed": missed,
        "median_latency_days": float(np.median(latencies)) if latencies else None,
        "mean_latency_days": round(float(np.mean(latencies)), 2) if latencies else None,
    }


def evaluate(
    labels: list[int | None], scores: list[float | None], predictions: list[int | None]
) -> dict:
    """Pairs are dropped where either the label or the score is missing, so
    every metric is computed over the same day set."""
    paired = [
        (label, score, pred)
        for label, score, pred in zip(labels, scores, predictions)
        if label is not None and score is not None and pred is not None
    ]
    if not paired:
        return {"evaluated_days": 0}

    y_true = [p[0] for p in paired]
    y_score = [p[1] for p in paired]
    y_pred = [p[2] for p in paired]

    return {
        "evaluated_days": len(paired),
        "positive_rate": round(sum(y_true) / len(y_true), 4),
        **classification_metrics(y_true, y_pred),
        **ranking_metrics(y_true, y_score),
        **calibration_metrics(y_true, y_score),
        "latency": detection_latency(labels, predictions),
    }
