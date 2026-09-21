ANOMALY_Z_THRESHOLD = 2.5


MAD_EPSILON = 1e-9


def robust_zscore(current: float, baseline_stats: dict) -> float:
    median = baseline_stats.get("median", 0.0)
    mad = baseline_stats.get("mad", 0.0)

    # Deliberately does not fall back to std: std is not robust to outliers,
    # so once a handful of genuinely anomalous days enter the baseline
    # population, std inflates from those same points and the z-score decays
    # right when persistence should be accumulating. MAD stays ~0 until
    # outliers are the majority, which is exactly the robustness we want.
    # When MAD itself is ~0 (a near-flat baseline with no real spread
    # estimate yet), fall back to a small fraction of the median instead.
    denom = mad if mad > MAD_EPSILON else max(abs(median) * 0.05, 1e-6)
    return round((current - median) / denom, 3)


def is_anomalous(z_score: float, threshold: float = ANOMALY_Z_THRESHOLD) -> bool:
    return abs(z_score) >= threshold
