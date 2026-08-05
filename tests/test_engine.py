from app.database import get_incident, list_incidents
from app.engine import IncidentEngine


def test_groups_repeated_events(settings):
    engine = IncidentEngine(settings)
    first = engine.ingest_line("app.log", "ERROR database connection timeout retry=1")
    second = engine.ingest_line("app.log", "ERROR database connection timeout retry=2")

    assert first["is_new"] is True
    assert second["is_new"] is False
    assert first["incident_id"] == second["incident_id"]

    row = get_incident(settings.database_path, first["incident_id"])
    assert row["count"] == 2
    assert len(row["events"]) == 2


def test_recovery_closes_open_incident(settings):
    engine = IncidentEngine(settings)
    created = engine.ingest_line("app.log", "ERROR payment gateway timeout order=8172")
    recovered = engine.ingest_line(
        "app.log", "INFO payment gateway recovered and success rate normal"
    )

    assert created["kind"] == "incident"
    assert recovered["kind"] == "recovery"
    row = get_incident(settings.database_path, created["incident_id"])
    assert row["status"] == "recovered"
    assert row["recovered_at"] is not None


def test_different_sources_create_different_incidents(settings):
    engine = IncidentEngine(settings)
    one = engine.ingest_line("api.log", "ERROR database connection timeout retry=1")
    two = engine.ingest_line("worker.log", "ERROR database connection timeout retry=1")
    assert one["incident_id"] != two["incident_id"]
    assert len(list_incidents(settings.database_path)) == 2
