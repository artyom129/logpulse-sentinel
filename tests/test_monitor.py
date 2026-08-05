from app.database import list_incidents
from app.engine import IncidentEngine
from app.monitor import LogMonitor


def test_monitor_reads_appended_lines_and_handles_truncation(settings):
    log = settings.monitored_files[0]
    log.write_text("ERROR database connection timeout retry=1\n", encoding="utf-8")

    monitor = LogMonitor(IncidentEngine(settings))
    assert monitor.tick() == 1
    assert len(list_incidents(settings.database_path)) == 1

    with log.open("a", encoding="utf-8") as handle:
        handle.write("ERROR database connection timeout retry=2\n")
    assert monitor.tick() == 1

    log.write_text("ERROR payment gateway timeout order=9\n", encoding="utf-8")
    assert monitor.tick() == 1
    assert len(list_incidents(settings.database_path)) == 2
