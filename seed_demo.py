from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import load_settings
from app.database import clear_all, init_db
from app.engine import IncidentEngine


settings = load_settings()
init_db(settings.database_path)
clear_all(settings.database_path)
engine = IncidentEngine(settings)

base = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=47)
source = str(settings.base_dir / "sample_logs" / "application.log")

events = [
    (0, "ERROR database connection timeout host=10.12.4.8 retry=1"),
    (1, "ERROR database connection timeout host=10.12.4.8 retry=2"),
    (2, "ERROR database connection timeout host=10.12.4.8 retry=3"),
    (8, "WARN auth failed login for user customer@example.com ip=192.168.1.52"),
    (9, "WARN auth failed login for user customer@example.com ip=192.168.1.53"),
    (14, "ERROR payment gateway timeout for order 8172 token=super-secret-token-value"),
    (15, "ERROR payment gateway timeout for order 8190 token=another-secret-token"),
    (20, "INFO database connection recovered and pool is healthy"),
    (25, "CRITICAL worker queue crashed: out of memory job_id=88214"),
    (26, "CRITICAL worker queue crashed: out of memory job_id=88215"),
    (30, "WARN filesystem usage reached 94% on /var/data"),
    (33, "INFO payment gateway recovered; success rate normal"),
    (37, "INFO worker restarted and queue healthy"),
]

for minutes, line in events:
    engine.ingest_line(
        source,
        line,
        created_at=(base + timedelta(minutes=minutes)).isoformat(),
    )

print("Demo incident history created.")
print(f"Database: {settings.database_path}")
print("Run: python run.py")
