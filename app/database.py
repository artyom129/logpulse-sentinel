from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    service TEXT NOT NULL,
    source TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'open',
    sample_message TEXT NOT NULL,
    recovered_at TEXT,
    acknowledged_at TEXT,
    resolved_manually INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_fingerprint ON incidents(fingerprint);
CREATE INDEX IF NOT EXISTS idx_incidents_last_seen ON incidents(last_seen DESC);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER,
    rule_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL,
    service TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(id)
);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at DESC);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def get_open_incident(db_path: str | Path, fingerprint: str) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM incidents
            WHERE fingerprint = ? AND status IN ('open', 'acknowledged')
            ORDER BY id DESC LIMIT 1
            """,
            (fingerprint,),
        ).fetchone()
    return dict(row) if row else None


def create_incident(
    db_path: str | Path,
    *,
    fingerprint: str,
    rule_id: str,
    title: str,
    severity: str,
    service: str,
    source: str,
    message: str,
    created_at: str,
) -> int:
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO incidents (
                fingerprint, rule_id, title, severity, service, source,
                first_seen, last_seen, count, status, sample_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'open', ?)
            """,
            (
                fingerprint,
                rule_id,
                title,
                severity,
                service,
                source,
                created_at,
                created_at,
                message,
            ),
        )
        return int(cursor.lastrowid)


def increment_incident(db_path: str | Path, incident_id: int, *, created_at: str) -> int:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE incidents SET count = count + 1, last_seen = ? WHERE id = ?",
            (created_at, incident_id),
        )
        row = conn.execute("SELECT count FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    return int(row["count"])


def insert_event(
    db_path: str | Path,
    *,
    incident_id: int | None,
    rule_id: str,
    kind: str,
    severity: str,
    service: str,
    source: str,
    message: str,
    created_at: str,
) -> int:
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO events (
                incident_id, rule_id, kind, severity, service, source, message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                rule_id,
                kind,
                severity,
                service,
                source,
                message,
                created_at,
            ),
        )
        return int(cursor.lastrowid)


def recover_incidents(
    db_path: str | Path,
    *,
    rule_id: str,
    source: str,
    recovered_at: str,
) -> list[int]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id FROM incidents
            WHERE rule_id = ? AND source = ? AND status IN ('open', 'acknowledged')
            """,
            (rule_id, source),
        ).fetchall()
        ids = [int(row["id"]) for row in rows]
        if ids:
            conn.executemany(
                """
                UPDATE incidents
                SET status = 'recovered', recovered_at = ?, last_seen = ?
                WHERE id = ?
                """,
                [(recovered_at, recovered_at, item) for item in ids],
            )
    return ids


def list_incidents(
    db_path: str | Path,
    *,
    status: str | None = None,
    severity: str | None = None,
    query: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if query:
        clauses.append(
            "(title LIKE ? OR service LIKE ? OR source LIKE ? OR sample_message LIKE ?)"
        )
        wildcard = f"%{query}%"
        params.extend([wildcard] * 4)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM incidents {where} ORDER BY last_seen DESC, id DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_incident(db_path: str | Path, incident_id: int) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        if not row:
            return None
        incident = dict(row)
        events = conn.execute(
            "SELECT * FROM events WHERE incident_id = ? ORDER BY created_at DESC LIMIT 250",
            (incident_id,),
        ).fetchall()
    incident["events"] = [dict(item) for item in events]
    return incident


def acknowledge_incident(db_path: str | Path, incident_id: int) -> bool:
    now = utc_now()
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE incidents
            SET status = 'acknowledged', acknowledged_at = ?
            WHERE id = ? AND status = 'open'
            """,
            (now, incident_id),
        )
    return cursor.rowcount > 0


def resolve_incident(db_path: str | Path, incident_id: int) -> bool:
    now = utc_now()
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE incidents
            SET status = 'resolved', recovered_at = ?, last_seen = ?, resolved_manually = 1
            WHERE id = ? AND status IN ('open', 'acknowledged')
            """,
            (now, now, incident_id),
        )
    return cursor.rowcount > 0


def dashboard_stats(db_path: str | Path) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    with connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM incidents").fetchone()["n"]
        open_count = conn.execute(
            "SELECT COUNT(*) AS n FROM incidents WHERE status IN ('open', 'acknowledged')"
        ).fetchone()["n"]
        critical = conn.execute(
            """
            SELECT COUNT(*) AS n FROM incidents
            WHERE severity = 'critical' AND status IN ('open', 'acknowledged')
            """
        ).fetchone()["n"]
        events_today = conn.execute(
            "SELECT COUNT(*) AS n FROM events WHERE substr(created_at, 1, 10) = ?",
            (today,),
        ).fetchone()["n"]
        rows = conn.execute(
            """
            SELECT first_seen, recovered_at FROM incidents
            WHERE recovered_at IS NOT NULL
            """
        ).fetchall()

    durations: list[float] = []
    for row in rows:
        try:
            start = datetime.fromisoformat(row["first_seen"])
            end = datetime.fromisoformat(row["recovered_at"])
            durations.append(max((end - start).total_seconds(), 0))
        except (TypeError, ValueError):
            continue
    mttr_minutes = round(sum(durations) / len(durations) / 60, 1) if durations else 0.0
    return {
        "total": int(total),
        "open": int(open_count),
        "critical": int(critical),
        "events_today": int(events_today),
        "mttr_minutes": mttr_minutes,
    }


def recent_events(db_path: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_all(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM incidents")
