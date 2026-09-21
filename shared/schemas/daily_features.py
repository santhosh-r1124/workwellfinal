from pydantic import BaseModel


class DailyFeatureVector(BaseModel):
    employee_id: str
    date: str

    work_duration: float = 0.0
    after_hours: float = 0.0
    break_count: int = 0
    average_break_gap: float = 0.0
    meeting_hours: float = 0.0
    context_switches: int = 0
    focus_minutes: float = 0.0
    typing_speed: float = 0.0
    typing_pause_rate: float = 0.0

    self_report_stress: float | None = None
    self_report_energy: float | None = None
    self_report_recovery: float | None = None


class DerivedFeatureVector(BaseModel):
    employee_id: str
    date: str

    overtime_frequency: float = 0.0
    after_hours_frequency: float = 0.0
    weekend_work_frequency: float = 0.0
    meeting_load: float = 0.0
    meeting_growth: float = 0.0
    break_debt: float = 0.0
    recovery_gap: float = 0.0
    context_switch_rate: float = 0.0
    focus_fragmentation: float = 0.0
    typing_deviation: float = 0.0
    communication_pressure: float = 0.0
    workload_growth: float = 0.0
    self_report_trend: float = 0.0
