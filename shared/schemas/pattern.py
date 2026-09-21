from pydantic import BaseModel


class SignalChange(BaseModel):
    name: str
    change: float
    anomalous_days: int = 0


class PatternObject(BaseModel):
    employee_id: str
    date: str
    state: str
    confidence: float
    duration_days: int
    signals: list[SignalChange]
    data_not_used: list[str] = []
