from datetime import date as date_type

import numpy as np
from scipy import stats

from shared.constants.wellbeing import BASELINE_MIN_DAYS

MAD_SCALE = 1.4826  # scales MAD to be a consistent estimator of std for normal data


def compute_baseline(values: list[float], dates: list[date_type] | None = None) -> dict:
    """Robust personal baseline statistics for one metric.

    Uses median/MAD rather than mean/std as the primary descriptors since
    workplace behavioral data contains outliers (a single all-nighter
    shouldn't dominate an employee's 'normal').
    """
    arr = np.array([v for v in values if v is not None], dtype=float)
    if arr.size == 0:
        return _empty_baseline()

    median = float(np.median(arr))
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    mad = float(np.median(np.abs(arr - median))) * MAD_SCALE
    rolling_avg = float(np.mean(arr[-7:]))
    trend = _linear_trend(arr)
    seasonality = _weekday_seasonality(arr, dates) if dates else {}

    return {
        "baseline": median,
        "median": median,
        "mean": mean,
        "std": std,
        "mad": mad,
        "rolling_avg": rolling_avg,
        "trend": trend,
        "seasonality": seasonality,
        "window_days": int(arr.size),
        "is_reliable": arr.size >= BASELINE_MIN_DAYS,
    }


def _empty_baseline() -> dict:
    return {
        "baseline": 0.0,
        "median": 0.0,
        "mean": 0.0,
        "std": 0.0,
        "mad": 0.0,
        "rolling_avg": 0.0,
        "trend": 0.0,
        "seasonality": {},
        "window_days": 0,
        "is_reliable": False,
    }


def _linear_trend(arr: np.ndarray) -> float:
    if arr.size < 2:
        return 0.0
    x = np.arange(arr.size)
    result = stats.linregress(x, arr)
    return float(result.slope)


def _weekday_seasonality(arr: np.ndarray, dates: list[date_type]) -> dict:
    buckets: dict[int, list[float]] = {}
    for v, d in zip(arr, dates):
        buckets.setdefault(d.weekday(), []).append(float(v))
    return {str(k): round(float(np.mean(v)), 2) for k, v in buckets.items()}


def deviation(current: float, baseline_stats: dict) -> float:
    """Matches the product's chosen presentation: simple difference from the
    robust baseline (median), e.g. baseline 8.4 vs current 10.1 -> +1.7."""
    return round(current - baseline_stats.get("baseline", 0.0), 2)
