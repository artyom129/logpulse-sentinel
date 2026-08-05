from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from app.config import load_settings
from app.database import init_db


@pytest.fixture
def settings(tmp_path: Path):
    base = load_settings(Path(__file__).resolve().parent.parent / "config.toml")
    configured = replace(
        base,
        database_path=tmp_path / "test.db",
        monitored_files=(tmp_path / "test.log",),
        telegram_enabled=False,
        start_at_end=False,
    )
    init_db(configured.database_path)
    return configured
