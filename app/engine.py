from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .config import Settings
from .database import (
    create_incident,
    get_open_incident,
    increment_incident,
    insert_event,
    recover_incidents,
)
from .detector import Detection, Detector


Notifier = Callable[[str], None]


class IncidentEngine:
    def __init__(self, settings: Settings, notifier: Notifier | None = None):
        self.settings = settings
        self.db_path = settings.database_path
        self.detector = Detector(settings)
        self.notifier = notifier

    @staticmethod
    def _timestamp(value: str | None = None) -> str:
        if value:
            return datetime.fromisoformat(value).astimezone(timezone.utc).replace(
                microsecond=0
            ).isoformat()
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def _normalize_message(message: str) -> str:
        value = message.lower()
        value = re.sub(r"\b\d+\b", "#", value)
        value = re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27,}", "<uuid>", value, flags=re.I)
        value = re.sub(r"\s+", " ", value).strip()
        return value[:500]

    def fingerprint(self, detection: Detection, source: str) -> str:
        material = "|".join(
            [
                detection.rule_id,
                Path(source).name.lower(),
                self._normalize_message(detection.message),
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def ingest_line(
        self,
        source: str,
        line: str,
        *,
        created_at: str | None = None,
    ) -> dict | None:
        detection = self.detector.detect(line)
        if not detection:
            return None
        timestamp = self._timestamp(created_at)

        if detection.kind == "recovery":
            recovered_ids = recover_incidents(
                self.db_path,
                rule_id=detection.rule_id,
                source=source,
                recovered_at=timestamp,
            )
            insert_event(
                self.db_path,
                incident_id=recovered_ids[0] if recovered_ids else None,
                rule_id=detection.rule_id,
                kind="recovery",
                severity=detection.severity,
                service=detection.service,
                source=source,
                message=detection.message,
                created_at=timestamp,
            )
            if recovered_ids and self.notifier:
                self.notifier(
                    f"✅ RECOVERED\n{detection.title}\n"
                    f"Source: {source}\nClosed incidents: {len(recovered_ids)}"
                )
            return {
                "kind": "recovery",
                "incident_ids": recovered_ids,
                "rule_id": detection.rule_id,
            }

        fingerprint = self.fingerprint(detection, source)
        existing = get_open_incident(self.db_path, fingerprint)
        is_new = existing is None

        if existing:
            incident_id = int(existing["id"])
            count = increment_incident(self.db_path, incident_id, created_at=timestamp)
        else:
            incident_id = create_incident(
                self.db_path,
                fingerprint=fingerprint,
                rule_id=detection.rule_id,
                title=detection.title,
                severity=detection.severity,
                service=detection.service,
                source=source,
                message=detection.message,
                created_at=timestamp,
            )
            count = 1

        insert_event(
            self.db_path,
            incident_id=incident_id,
            rule_id=detection.rule_id,
            kind="incident",
            severity=detection.severity,
            service=detection.service,
            source=source,
            message=detection.message,
            created_at=timestamp,
        )

        should_repeat_alert = (
            not is_new
            and count > 1
            and count % self.settings.repeat_alert_every == 0
        )
        if self.notifier and (is_new or should_repeat_alert):
            prefix = "🚨 NEW INCIDENT" if is_new else "⚠️ INCIDENT REPEATING"
            self.notifier(
                f"{prefix}\n"
                f"{detection.title}\n"
                f"Severity: {detection.severity.upper()}\n"
                f"Service: {detection.service}\n"
                f"Source: {source}\n"
                f"Count: {count}\n"
                f"{detection.message[:500]}"
            )

        return {
            "kind": "incident",
            "incident_id": incident_id,
            "is_new": is_new,
            "count": count,
            "rule_id": detection.rule_id,
        }
