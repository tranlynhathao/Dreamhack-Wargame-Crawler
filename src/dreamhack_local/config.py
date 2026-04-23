"""Configuration loading and persistence."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def discover_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_dir() -> Path:
    if os.environ.get("XDG_CONFIG_HOME"):
        return Path(os.environ["XDG_CONFIG_HOME"]) / "dreamhack-local"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "dreamhack-local"
    return Path.home() / ".config" / "dreamhack-local"


def read_settings_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


class AppSettings(BaseSettings):
    """Runtime settings loaded from env and a small local config file."""

    model_config = SettingsConfigDict(env_prefix="DH_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    repo_root: Path = Field(default_factory=discover_repo_root)
    base_url: str = "https://dreamhack.io"
    wargame_path: str = "/wargame"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    request_delay_seconds: float = 1.0
    log_level: str = "INFO"
    workspace_root: Path | None = None
    database_path: Path | None = None
    manifest_export_path: Path | None = None
    config_dir: Path | None = None
    settings_store_path: Path | None = None
    session_store_path: Path | None = None
    enable_localhost_cors: bool = True
    max_listing_pages: int = 100

    @model_validator(mode="after")
    def populate_paths(self) -> "AppSettings":
        repo_root = self.repo_root.resolve()
        config_dir = (self.config_dir or default_config_dir()).resolve()
        workspace_root = (self.workspace_root or repo_root).resolve()
        database_path = (self.database_path or repo_root / "data" / "dreamhack_local.db").resolve()
        manifest_export_path = (self.manifest_export_path or repo_root / "manifest.json").resolve()
        settings_store_path = (self.settings_store_path or config_dir / "settings.json").resolve()
        session_store_path = (self.session_store_path or config_dir / "session.json").resolve()

        config_dir.mkdir(parents=True, exist_ok=True)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        workspace_root.mkdir(parents=True, exist_ok=True)

        self.repo_root = repo_root
        self.config_dir = config_dir
        self.workspace_root = workspace_root
        self.database_path = database_path
        self.manifest_export_path = manifest_export_path
        self.settings_store_path = settings_store_path
        self.session_store_path = session_store_path
        return self

    @property
    def wargame_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.wargame_path}"


def load_settings() -> AppSettings:
    config_dir = default_config_dir()
    file_settings = read_settings_file(config_dir / "settings.json")
    file_settings.setdefault("repo_root", str(discover_repo_root()))
    return AppSettings(**file_settings)


def save_settings_override(**updates: Any) -> AppSettings:
    settings = load_settings()
    path = settings.settings_store_path
    current = read_settings_file(path)
    current.update(updates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    return load_settings()
