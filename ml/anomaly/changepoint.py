import numpy as np


def cusum_changepoint(values: list[float], threshold_std: float = 1.5) -> int | None:
    """Two-sided CUSUM changepoint detector. Returns the index where a
    sustained shift begins, or None if no shift is detected."""
    arr = np.array(values, dtype=float)
    if arr.size < 4:
        return None

    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) or 1.0
    threshold = threshold_std * std

    pos, neg = 0.0, 0.0
    for i, v in enumerate(arr):
        deviation = v - mean
        pos = max(0.0, pos + deviation - 0.5 * std)
        neg = min(0.0, neg + deviation + 0.5 * std)
        if pos > threshold or neg < -threshold:
            return i
    return None
