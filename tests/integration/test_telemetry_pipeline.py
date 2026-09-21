from datetime import datetime, timedelta, timezone

from apps.backend.services import baseline_service, telemetry_service
from tests.integration.conftest import make_user


def test_ingest_and_recompute_builds_daily_feature(db_session, org):
    employee = make_user(db_session, org, "employee", "emp_telemetry1", "telemetry1@example.com")
    today = datetime.now(timezone.utc)

    telemetry_service.ingest_event(
        db_session, employee.id, today, {"active_minutes": 120, "typing_speed": 55.0}
    )
    daily = telemetry_service.recompute_daily_feature(db_session, employee.id, today.date())

    assert daily.work_duration == 2.0
    assert daily.typing_speed == 55.0


def test_baseline_deviation_reflects_current_vs_history(db_session, org):
    employee = make_user(db_session, org, "employee", "emp_telemetry2", "telemetry2@example.com")
    base_day = datetime.now(timezone.utc) - timedelta(days=10)

    for i in range(9):
        day = base_day + timedelta(days=i)
        telemetry_service.ingest_event(db_session, employee.id, day, {"active_minutes": 480})
        telemetry_service.recompute_daily_feature(db_session, employee.id, day.date())

    spike_day = base_day + timedelta(days=9)
    telemetry_service.ingest_event(db_session, employee.id, spike_day, {"active_minutes": 720})
    telemetry_service.recompute_daily_feature(db_session, employee.id, spike_day.date())

    baseline_service.recompute_baselines(db_session, employee.id)
    response = baseline_service.get_baseline_response(db_session, employee.id)

    work_duration = response["metrics"]["work_duration"]
    assert work_duration["current"] == 12.0
    assert work_duration["deviation"] > 0
