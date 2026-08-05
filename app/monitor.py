from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .engine import IncidentEngine


@dataclass
class FileState:
    offset: int
    identity: tuple[int, int] | None


class LogMonitor:
    def __init__(self, engine: IncidentEngine):
        self.engine = engine
        self.settings = engine.settings
        self.states: dict[Path, FileState] = {}

    @staticmethod
    def _identity(path: Path) -> tuple[int, int] | None:
        try:
            stat = path.stat()
            return int(stat.st_dev), int(stat.st_ino)
        except OSError:
            return None

    def _initial_offset(self, path: Path) -> int:
        if self.settings.start_at_end:
            try:
                return path.stat().st_size
            except OSError:
                return 0
        return 0

    def tick_file(self, path: Path) -> int:
        if not path.exists() or not path.is_file():
            return 0

        identity = self._identity(path)
        size = path.stat().st_size
        state = self.states.get(path)

        if state is None:
            state = FileState(self._initial_offset(path), identity)
            self.states[path] = state
        elif state.identity != identity or size < state.offset:
            state.offset = 0
            state.identity = identity

        processed = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(state.offset)
            for line in handle:
                if line.strip():
                    self.engine.ingest_line(str(path), line)
                    processed += 1
            state.offset = handle.tell()
        return processed

    def tick(self) -> int:
        return sum(self.tick_file(path) for path in self.settings.monitored_files)
