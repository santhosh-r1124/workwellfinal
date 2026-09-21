def compute_ewma(values: list[float], alpha: float = 0.3) -> list[float]:
    if not values:
        return []
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def ewma_deviation(values: list[float], alpha: float = 0.3) -> float:
    """Deviation of the latest value from the smoothed trend of everything
    before it - detects a fresh shift even when the raw baseline is noisy."""
    if len(values) < 2:
        return 0.0
    smoothed = compute_ewma(values[:-1], alpha=alpha)
    return round(values[-1] - smoothed[-1], 3)
