from ml.anomaly.ewma import compute_ewma, ewma_deviation
from ml.anomaly.persistence import consecutive_anomalous_days, is_persistent_pattern
from ml.anomaly.zscore import is_anomalous, robust_zscore
from ml.baseline.baseline_engine import compute_baseline


def test_robust_zscore_flags_large_deviation():
    stable = [8.0] * 10
    baseline = compute_baseline(stable)
    z = robust_zscore(15.0, baseline)
    assert is_anomalous(z)


def test_robust_zscore_no_flag_for_similar_value():
    stable = [8.0, 8.1, 7.9, 8.2, 7.8, 8.0, 8.1]
    baseline = compute_baseline(stable)
    z = robust_zscore(8.05, baseline)
    assert not is_anomalous(z)


def test_consecutive_anomalous_days_resets_on_normal_day():
    flags = [True, True, False, True, True, True]
    assert consecutive_anomalous_days(flags) == 3


def test_is_persistent_pattern_requires_min_days():
    assert not is_persistent_pattern([True, True, True, False])
    assert is_persistent_pattern([True, True, True, True, True])


def test_ewma_smooths_and_deviation_detects_shift():
    values = [8.0, 8.1, 7.9, 8.0, 8.1, 15.0]
    smoothed = compute_ewma(values[:-1])
    assert len(smoothed) == len(values) - 1
    dev = ewma_deviation(values)
    assert dev > 5
