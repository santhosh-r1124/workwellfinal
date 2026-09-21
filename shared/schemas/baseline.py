from pydantic import BaseModel


class MetricBaseline(BaseModel):
    metric: str
    baseline: float
    current: float
    deviation: float
    median: float
    mean: float
    std: float
    mad: float
    rolling_avg: float
    trend: float
    window_days: int


class BaselineResponse(BaseModel):
    employee_id: str
    metrics: dict[str, MetricBaseline]
