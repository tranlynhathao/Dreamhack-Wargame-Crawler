from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("DH_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    monkeypatch.setenv("DH_DATABASE_PATH", str(tmp_path / "data" / "dreamhack_local.db"))
    monkeypatch.setenv("DH_MANIFEST_EXPORT_PATH", str(tmp_path / "manifest.json"))
    monkeypatch.setenv("DH_REQUEST_DELAY_SECONDS", "0")
    monkeypatch.setenv("DH_LOG_LEVEL", "CRITICAL")
    yield
