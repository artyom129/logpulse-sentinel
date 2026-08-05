from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Callable

from .config import Settings


class TelegramClient:
    def __init__(self, settings: Settings, stats_provider: Callable[[], dict] | None = None):
        self.settings = settings
        self.stats_provider = stats_provider
        self.offset = 0

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.telegram_enabled
            and self.settings.telegram_token
            and self.settings.telegram_chat_id
        )

    @property
    def base_url(self) -> str:
        return f"https://api.telegram.org/bot{self.settings.telegram_token}"

    def _request(self, method: str, payload: dict) -> dict:
        body = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/{method}",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))

    def send(self, text: str) -> None:
        if not self.enabled:
            return
        try:
            self._request(
                "sendMessage",
                {
                    "chat_id": self.settings.telegram_chat_id,
                    "text": text[:4000],
                    "disable_web_page_preview": "true",
                },
            )
        except Exception:
            return

    def command_reply(self, text: str) -> str:
        command = text.strip().split()[0].lower()
        stats = self.stats_provider() if self.stats_provider else {}
        if command == "/status":
            return (
                "📊 LogPulse status\n"
                f"Open: {stats.get('open', 0)}\n"
                f"Critical: {stats.get('critical', 0)}\n"
                f"Events today: {stats.get('events_today', 0)}\n"
                f"MTTR: {stats.get('mttr_minutes', 0)} min"
            )
        if command == "/open":
            return (
                f"🚨 Open incidents: {stats.get('open', 0)}\n"
                f"Critical: {stats.get('critical', 0)}"
            )
        if command == "/today":
            return f"🗓 Events today: {stats.get('events_today', 0)}"
        return "Commands: /status /open /today"

    def poll_once(self) -> int:
        if not self.enabled or not self.settings.telegram_poll_commands:
            return 0
        try:
            payload = self._request(
                "getUpdates",
                {
                    "offset": self.offset,
                    "timeout": 2,
                    "allowed_updates": json.dumps(["message"]),
                },
            )
        except Exception:
            return 0

        handled = 0
        for item in payload.get("result", []):
            self.offset = max(self.offset, int(item.get("update_id", 0)) + 1)
            message = item.get("message") or {}
            chat_id = str((message.get("chat") or {}).get("id", ""))
            text = str(message.get("text", ""))
            if chat_id != str(self.settings.telegram_chat_id) or not text.startswith("/"):
                continue
            self.send(self.command_reply(text))
            handled += 1
        return handled
