from datetime import date, timedelta

from ml.baseline.baseline_engine import compute_baseline, deviation


def test_compute_baseline_on_stable_values():
    values = [8.0, 8.2, 7.9, 8.1, 8.0, 7.8, 8.3]
    stats = compute_baseline(values)
    assert stats["is_reliable"] is True
    assert 7.8 <= stats["median"] <= 8.3
    assert stats["window_days"] == 7


def test_compute_baseline_empty():
    stats = compute_baseline([])
    assert stats["window_days"] == 0
    assert stats["is_reliable"] is False


def test_deviation_matches_simple_difference():
    stats = {"baseline": 8.4}
    assert deviation(10.1, stats) == 1.7
    assert deviation(4.8, {"baseline": 2.7}) == 2.1


def test_baseline_trend_detects_upward_slope():
    values = [8.0, 8.5, 9.0, 9.5, 10.0]
    stats = compute_baseline(values)
    assert stats["trend"] > 0


def test_baseline_seasonality_buckets_by_weekday():
    start = date(2026, 1, 5)  # Monday
    dates = [start + timedelta(days=i) for i in range(7)]
    values = [8.0] * 7
    stats = compute_baseline(values, dates)
    assert set(stats["seasonality"].keys()) == {str(i) for i in range(7)}
