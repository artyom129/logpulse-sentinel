from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: str
    service: str
    pattern: str
    recovery_pattern: str | None = None


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    app_name: str
    database_path: Path
    max_incidents_on_dashboard: int
    scan_interval_seconds: float
    dedupe_window_seconds: int
    repeat_alert_every: int
    start_at_end: bool
    monitored_files: tuple[Path, ...]
    redact_emails: bool
    redact_ipv4: bool
    redact_tokens: bool
    extra_redact_patterns: tuple[str, ...]
    telegram_enabled: bool
    telegram_poll_commands: bool
    telegram_poll_interval_seconds: int
    telegram_token: str
    telegram_chat_id: str
    rules: tuple[Rule, ...]


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def load_settings(config_path: str | Path | None = None) -> Settings:
    path = Path(config_path or os.getenv("LOGPULSE_CONFIG", "config.toml")).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    data: dict[str, Any]
    with path.open("rb") as handle:
        data = tomllib.load(handle)

    base = path.parent
    app = data.get("app", {})
    monitor = data.get("monitor", {})
    privacy = data.get("privacy", {})
    telegram = data.get("telegram", {})

    rules = tuple(
        Rule(
            id=str(item["id"]),
            title=str(item["title"]),
            severity=str(item.get("severity", "medium")).lower(),
            service=str(item.get("service", "application")),
            pattern=str(item["pattern"]),
            recovery_pattern=str(item["recovery_pattern"]) if item.get("recovery_pattern") else None,
        )
        for item in data.get("rules", [])
    )
    if not rules:
        raise ValueError("At least one detection rule is required")

    for rule in rules:
        re.compile(rule.pattern)
        if rule.recovery_pattern:
            re.compile(rule.recovery_pattern)

    return Settings(
        base_dir=base,
        app_name=str(app.get("name", "LogPulse Sentinel")),
        database_path=_resolve(base, str(app.get("database_path", "data/logpulse.db"))),
        max_incidents_on_dashboard=int(app.get("max_incidents_on_dashboard", 100)),
        scan_interval_seconds=max(float(monitor.get("scan_interval_seconds", 1.0)), 0.1),
        dedupe_window_seconds=max(int(monitor.get("dedupe_window_seconds", 300)), 1),
        repeat_alert_every=max(int(monitor.get("repeat_alert_every", 25)), 1),
        start_at_end=bool(monitor.get("start_at_end", True)),
        monitored_files=tuple(_resolve(base, str(item)) for item in monitor.get("files", [])),
        redact_emails=bool(privacy.get("redact_emails", True)),
        redact_ipv4=bool(privacy.get("redact_ipv4", True)),
        redact_tokens=bool(privacy.get("redact_tokens", True)),
        extra_redact_patterns=tuple(str(item) for item in privacy.get("extra_patterns", [])),
        telegram_enabled=bool(telegram.get("enabled", False)),
        telegram_poll_commands=bool(telegram.get("poll_commands", True)),
        telegram_poll_interval_seconds=max(int(telegram.get("poll_interval_seconds", 10)), 5),
        telegram_token=os.getenv("LOGPULSE_TELEGRAM_TOKEN", ""),
        telegram_chat_id=os.getenv("LOGPULSE_TELEGRAM_CHAT_ID", ""),
        rules=rules,
    )
