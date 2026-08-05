from __future__ import annotations

import re
from dataclasses import dataclass

from .config import Settings


@dataclass(frozen=True)
class Detection:
    rule_id: str
    title: str
    severity: str
    service: str
    kind: str
    message: str


class Detector:
    EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
    IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    TOKEN = re.compile(
        r"(?i)\b(?:token|api[_-]?key|secret|session)[=:]\s*[A-Za-z0-9._~+/=-]{8,}"
    )

    def __init__(self, settings: Settings):
        self.settings = settings
        self.compiled = [
            (
                rule,
                re.compile(rule.pattern),
                re.compile(rule.recovery_pattern) if rule.recovery_pattern else None,
            )
            for rule in settings.rules
        ]
        self.extra_redactors = [re.compile(pattern) for pattern in settings.extra_redact_patterns]

    def redact(self, text: str) -> str:
        value = text.strip()
        if self.settings.redact_emails:
            value = self.EMAIL.sub("[redacted-email]", value)
        if self.settings.redact_ipv4:
            value = self.IPV4.sub("[redacted-ip]", value)
        if self.settings.redact_tokens:
            value = self.TOKEN.sub("[redacted-token]", value)
        for pattern in self.extra_redactors:
            value = pattern.sub("[redacted]", value)
        return value

    def detect(self, line: str) -> Detection | None:
        clean = self.redact(line)
        for rule, pattern, recovery in self.compiled:
            if recovery and recovery.search(clean):
                return Detection(
                    rule.id,
                    rule.title,
                    rule.severity,
                    rule.service,
                    "recovery",
                    clean,
                )
            if pattern.search(clean):
                return Detection(
                    rule.id,
                    rule.title,
                    rule.severity,
                    rule.service,
                    "incident",
                    clean,
                )
        return None
