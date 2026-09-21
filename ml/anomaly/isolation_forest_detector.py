import numpy as np
from sklearn.ensemble import IsolationForest


def multivariate_anomaly_scores(feature_matrix: list[list[float]], contamination: float = 0.1) -> list[float]:
    """Given rows of an employee's own historical multi-signal feature
    vectors, return an anomaly score per row (higher = more anomalous).
    Requires enough history to fit (>= 10 rows); returns zeros otherwise."""
    arr = np.array(feature_matrix, dtype=float)
    if arr.shape[0] < 10:
        return [0.0] * arr.shape[0]

    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(arr)
    raw_scores = model.decision_function(arr)  # higher = more normal
    return [round(float(-s), 3) for s in raw_scores]
