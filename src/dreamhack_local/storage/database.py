"""SQLite database setup."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS challenges (
    challenge_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    url TEXT NOT NULL,
    category TEXT,
    category_display TEXT,
    difficulty INTEGER,
    difficulty_label TEXT,
    status TEXT,
    author TEXT,
    solvers INTEGER,
    has_attachments INTEGER NOT NULL DEFAULT 0,
    downloaded INTEGER NOT NULL DEFAULT 0,
    local_path TEXT,
    description_text TEXT,
    description_html TEXT,
    parse_warnings TEXT NOT NULL DEFAULT '[]',
    last_error TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    first_seen TEXT,
    last_seen TEXT,
    last_crawled_at TEXT,
    last_downloaded_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_challenges_category ON challenges(category);
CREATE INDEX IF NOT EXISTS idx_challenges_difficulty ON challenges(difficulty);
CREATE INDEX IF NOT EXISTS idx_challenges_downloaded ON challenges(downloaded);
CREATE INDEX IF NOT EXISTS idx_challenges_slug ON challenges(slug);

CREATE TABLE IF NOT EXISTS challenge_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    source_url TEXT,
    content_type TEXT,
    size_bytes INTEGER,
    checksum_sha256 TEXT,
    status TEXT NOT NULL DEFAULT 'downloaded',
    last_error TEXT,
    downloaded_at TEXT,
    FOREIGN KEY(challenge_id) REFERENCES challenges(challenge_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_challenge_files_challenge ON challenge_files(challenge_id);

CREATE TABLE IF NOT EXISTS crawl_runs (
    run_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    filters_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'running',
    pages_seen INTEGER NOT NULL DEFAULT 0,
    challenges_seen INTEGER NOT NULL DEFAULT 0,
    challenges_updated INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    summary_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    created_at TEXT,
    started_at TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_state (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    cookies_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'missing',
    message TEXT NOT NULL DEFAULT '',
    updated_at TEXT,
    last_checked_at TEXT
);
"""


class Database:
    """Small sqlite wrapper that provides new connections per operation."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
