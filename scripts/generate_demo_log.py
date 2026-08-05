from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
LOG = BASE / "sample_logs" / "application.log"

messages = [
    "INFO api request completed status=200 duration_ms=84",
    "INFO checkout created order_id=8172",
    "ERROR database connection timeout host=10.12.4.8 retry=1",
    "ERROR database connection timeout host=10.12.4.8 retry=2",
    "WARN auth failed login for user customer@example.com ip=192.168.1.52",
    "ERROR payment gateway timeout for order 8172 token=super-secret-token-value",
    "CRITICAL worker queue crashed: out of memory job_id=88214",
    "WARN filesystem usage reached 94% on /var/data",
    "INFO database connection recovered and pool is healthy",
    "INFO payment gateway recovered; success rate normal",
    "INFO worker restarted and queue healthy",
    "INFO filesystem usage normal below threshold",
]

print(f"Appending demo events to {LOG}")
print("Press Ctrl+C to stop.")

while True:
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    message = random.choice(messages)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")
    print(message)
    time.sleep(random.uniform(1.2, 3.2))
