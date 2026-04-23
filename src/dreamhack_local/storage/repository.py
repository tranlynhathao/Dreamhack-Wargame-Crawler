"""Data access helpers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from dreamhack_local.models.schemas import ChallengeFileRecord, ChallengeRecord, JobRecord, SessionInfo, StatsResponse
from dreamhack_local.storage.database import Database
from dreamhack_local.utils.normalization import extract_challenge_id, slugify_title


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AppRepository:
    """SQLite repository for application state."""

    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _load_json(value: str | None, default: Any) -> Any:
        if value in (None, ""):
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    def _derive_download_status(self, row: Any, metadata: dict[str, Any]) -> str:
        file_count = int(row["file_count"] or 0)
        byte_count = int(row["byte_count"] or 0)
        expected_downloads = len(metadata.get("download_urls") or [])
        has_description = bool(row["description_text"] or row["description_html"])
        has_local_path = bool(row["local_path"])
        has_error = bool(row["last_error"])

        if has_error:
            return "partial" if file_count > 0 or byte_count > 0 else "failed"
        if file_count > 0 or byte_count > 0:
            if expected_downloads and file_count < expected_downloads:
                return "partial"
            return "files_downloaded"
        if has_description:
            return "description_saved"
        if has_local_path or metadata:
            return "metadata_only"
        return "not_downloaded"

    @staticmethod
    def _challenge_select_fields(alias: str = "c") -> str:
        return f"""
            {alias}.*,
            (
                SELECT COUNT(*)
                FROM challenge_files f
                WHERE f.challenge_id = {alias}.challenge_id AND f.status = 'downloaded'
            ) AS file_count,
            (
                SELECT COALESCE(SUM(f.size_bytes), 0)
                FROM challenge_files f
                WHERE f.challenge_id = {alias}.challenge_id AND f.status = 'downloaded'
            ) AS byte_count
        """

    def _row_to_challenge(self, row: Any) -> ChallengeRecord:
        metadata = self._load_json(row["metadata_json"], {})
        download_status = self._derive_download_status(row, metadata)
        return ChallengeRecord.model_validate(
            {
                "challenge_id": row["challenge_id"],
                "title": row["title"],
                "slug": row["slug"],
                "url": row["url"],
                "category": row["category"],
                "category_display": row["category_display"],
                "difficulty": row["difficulty"],
                "difficulty_label": row["difficulty_label"],
                "status": row["status"],
                "author": row["author"],
                "solvers": row["solvers"],
                "has_attachments": bool(row["has_attachments"]),
                "downloaded": download_status in {"files_downloaded", "partial"},
                "local_path": row["local_path"],
                "description_text": row["description_text"],
                "description_html": row["description_html"],
                "download_status": download_status,
                "parse_warnings": self._load_json(row["parse_warnings"], []),
                "last_error": row["last_error"],
                "metadata": metadata,
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
                "last_crawled_at": row["last_crawled_at"],
                "last_downloaded_at": row["last_downloaded_at"],
                "file_count": row["file_count"],
                "byte_count": row["byte_count"],
            }
        )

    def _row_to_file(self, row: Any) -> ChallengeFileRecord:
        return ChallengeFileRecord.model_validate(
            {
                "id": row["id"],
                "challenge_id": row["challenge_id"],
                "filename": row["filename"],
                "relative_path": row["relative_path"],
                "source_url": row["source_url"],
                "content_type": row["content_type"],
                "size_bytes": row["size_bytes"],
                "checksum_sha256": row["checksum_sha256"],
                "status": row["status"],
                "last_error": row["last_error"],
                "downloaded_at": row["downloaded_at"],
            }
        )

    def challenge_count(self) -> int:
        with self.database.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM challenges").fetchone()
            return int(row["count"])

    def list_challenges(
        self,
        *,
        category: str | None = None,
        difficulty: int | None = None,
        status: str | None = None,
        author: str | None = None,
        downloaded: bool | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ChallengeRecord]:
        clauses: list[str] = []
        values: list[Any] = []

        if category is not None:
            clauses.append("category = ?")
            values.append(category)
        if difficulty is not None:
            clauses.append("difficulty = ?")
            values.append(difficulty)
        if status is not None:
            clauses.append("status = ?")
            values.append(status)
        if author is not None:
            clauses.append("author = ?")
            values.append(author)
        if downloaded is not None:
            clauses.append("downloaded = ?")
            values.append(1 if downloaded else 0)
        if search:
            clauses.append(
                "(title LIKE ? OR description_text LIKE ? OR slug LIKE ? OR CAST(challenge_id AS TEXT) LIKE ? OR url LIKE ?)"
            )
            token = f"%{search}%"
            values.extend([token, token, token, token, token])

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT
                {self._challenge_select_fields("c")}
            FROM challenges c
            {where_clause}
            ORDER BY c.challenge_id DESC
            LIMIT ? OFFSET ?
        """
        values.extend([limit, offset])

        with self.database.connect() as connection:
            rows = connection.execute(query, values).fetchall()
        return [self._row_to_challenge(row) for row in rows]

    def get_challenge(self, challenge_id: int) -> ChallengeRecord | None:
        query = """
            SELECT
                {fields}
            FROM challenges c
            WHERE c.challenge_id = ?
        """.format(fields=self._challenge_select_fields("c"))
        with self.database.connect() as connection:
            row = connection.execute(query, (challenge_id,)).fetchone()
        return self._row_to_challenge(row) if row else None

    def resolve_challenge(self, identifier: str) -> ChallengeRecord | None:
        challenge_id = extract_challenge_id(identifier)
        if challenge_id is not None:
            return self.get_challenge(challenge_id)

        lowered = identifier.strip().lower()
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    {fields}
                FROM challenges c
                WHERE lower(c.slug) = ? OR lower(c.title) = ?
                LIMIT 1
                """.format(fields=self._challenge_select_fields("c")),
                (lowered, lowered),
            ).fetchone()
        return self._row_to_challenge(row) if row else None

    def upsert_challenge(self, payload: dict[str, Any]) -> ChallengeRecord:
        challenge_id = int(payload["challenge_id"])
        existing = self.get_challenge(challenge_id)
        now = utcnow_iso()

        if existing:
            record = existing.model_dump(mode="json")
        else:
            record = {
                "challenge_id": challenge_id,
                "title": "",
                "slug": "",
                "url": "",
                "category": None,
                "category_display": None,
                "difficulty": None,
                "difficulty_label": None,
                "status": None,
                "author": None,
                "solvers": None,
                "has_attachments": False,
                "downloaded": False,
                "local_path": None,
                "description_text": None,
                "description_html": None,
                "parse_warnings": [],
                "last_error": None,
                "metadata": {},
                "first_seen": payload.get("first_seen") or now,
                "last_seen": payload.get("last_seen") or now,
                "last_crawled_at": None,
                "last_downloaded_at": None,
                "file_count": 0,
            }

        for key, value in payload.items():
            if key == "id":
                continue
            record[key] = value

        record["challenge_id"] = challenge_id
        record["slug"] = record.get("slug") or slugify_title(record.get("title"), fallback=str(challenge_id))
        record["last_seen"] = payload.get("last_seen") or now
        if not record.get("first_seen"):
            record["first_seen"] = now

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO challenges (
                    challenge_id, title, slug, url, category, category_display, difficulty, difficulty_label,
                    status, author, solvers, has_attachments, downloaded, local_path, description_text,
                    description_html, parse_warnings, last_error, metadata_json, first_seen, last_seen,
                    last_crawled_at, last_downloaded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(challenge_id) DO UPDATE SET
                    title = excluded.title,
                    slug = excluded.slug,
                    url = excluded.url,
                    category = excluded.category,
                    category_display = excluded.category_display,
                    difficulty = excluded.difficulty,
                    difficulty_label = excluded.difficulty_label,
                    status = excluded.status,
                    author = excluded.author,
                    solvers = excluded.solvers,
                    has_attachments = excluded.has_attachments,
                    downloaded = excluded.downloaded,
                    local_path = excluded.local_path,
                    description_text = excluded.description_text,
                    description_html = excluded.description_html,
                    parse_warnings = excluded.parse_warnings,
                    last_error = excluded.last_error,
                    metadata_json = excluded.metadata_json,
                    first_seen = excluded.first_seen,
                    last_seen = excluded.last_seen,
                    last_crawled_at = excluded.last_crawled_at,
                    last_downloaded_at = excluded.last_downloaded_at
                """,
                (
                    record["challenge_id"],
                    record["title"],
                    record["slug"],
                    record["url"],
                    record.get("category"),
                    record.get("category_display"),
                    record.get("difficulty"),
                    record.get("difficulty_label"),
                    record.get("status"),
                    record.get("author"),
                    record.get("solvers"),
                    1 if record.get("has_attachments") else 0,
                    1 if record.get("downloaded") else 0,
                    record.get("local_path"),
                    record.get("description_text"),
                    record.get("description_html"),
                    json.dumps(record.get("parse_warnings", []), ensure_ascii=False),
                    record.get("last_error"),
                    json.dumps(record.get("metadata", {}), ensure_ascii=False),
                    record.get("first_seen"),
                    record.get("last_seen"),
                    record.get("last_crawled_at"),
                    record.get("last_downloaded_at"),
                ),
            )

        saved = self.get_challenge(challenge_id)
        if not saved:
            raise RuntimeError(f"Challenge {challenge_id} was not saved")
        return saved

    def replace_challenge_files(self, challenge_id: int, files: list[ChallengeFileRecord | dict[str, Any]]) -> None:
        normalized: list[ChallengeFileRecord] = []
        for file_record in files:
            if isinstance(file_record, ChallengeFileRecord):
                normalized.append(file_record)
            else:
                normalized.append(ChallengeFileRecord.model_validate(file_record))

        with self.database.connect() as connection:
            connection.execute("DELETE FROM challenge_files WHERE challenge_id = ?", (challenge_id,))
            for file_record in normalized:
                connection.execute(
                    """
                    INSERT INTO challenge_files (
                        challenge_id, filename, relative_path, source_url, content_type, size_bytes,
                        checksum_sha256, status, last_error, downloaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        challenge_id,
                        file_record.filename,
                        file_record.relative_path,
                        file_record.source_url,
                        file_record.content_type,
                        file_record.size_bytes,
                        file_record.checksum_sha256,
                        file_record.status,
                        file_record.last_error,
                        file_record.downloaded_at.isoformat() if file_record.downloaded_at else None,
                    ),
                )

    def list_challenge_files(self, challenge_id: int) -> list[ChallengeFileRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM challenge_files
                WHERE challenge_id = ?
                ORDER BY filename ASC
                """,
                (challenge_id,),
            ).fetchall()
        return [self._row_to_file(row) for row in rows]

    def create_crawl_run(self, *, mode: str, filters: dict[str, Any]) -> str:
        run_id = str(uuid.uuid4())
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO crawl_runs (run_id, mode, filters_json, status, started_at)
                VALUES (?, ?, ?, 'running', ?)
                """,
                (run_id, mode, json.dumps(filters, ensure_ascii=False), utcnow_iso()),
            )
        return run_id

    def update_crawl_run(self, run_id: str, **fields: Any) -> None:
        if not fields:
            return
        columns = []
        values = []
        for key, value in fields.items():
            if key.endswith("_json") and not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            columns.append(f"{key} = ?")
            values.append(value)
        values.append(run_id)
        with self.database.connect() as connection:
            connection.execute(f"UPDATE crawl_runs SET {', '.join(columns)} WHERE run_id = ?", values)

    def create_job(self, *, kind: str, payload: dict[str, Any] | None = None) -> JobRecord:
        job_id = str(uuid.uuid4())
        created_at = utcnow_iso()
        payload = payload or {}
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (job_id, kind, status, progress, message, payload_json, result_json, created_at)
                VALUES (?, ?, 'queued', 0, '', ?, '{}', ?)
                """,
                (job_id, kind, json.dumps(payload, ensure_ascii=False), created_at),
            )
        job = self.get_job(job_id)
        if not job:
            raise RuntimeError(f"Job {job_id} was not created")
        return job

    def update_job(self, job_id: str, **fields: Any) -> JobRecord | None:
        if not fields:
            return self.get_job(job_id)
        columns = []
        values = []
        for key, value in fields.items():
            if key in {"payload", "result"} and not isinstance(value, str):
                key = f"{key}_json"
                value = json.dumps(value, ensure_ascii=False)
            columns.append(f"{key} = ?")
            values.append(value)
        values.append(job_id)
        with self.database.connect() as connection:
            connection.execute(f"UPDATE jobs SET {', '.join(columns)} WHERE job_id = ?", values)
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> JobRecord | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return JobRecord.model_validate(
            {
                "job_id": row["job_id"],
                "kind": row["kind"],
                "status": row["status"],
                "progress": row["progress"],
                "message": row["message"],
                "payload": self._load_json(row["payload_json"], {}),
                "result": self._load_json(row["result_json"], {}),
                "error": row["error"],
                "created_at": row["created_at"],
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
            }
        )

    def list_jobs(self, limit: int = 100) -> list[JobRecord]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [
            JobRecord.model_validate(
                {
                    "job_id": row["job_id"],
                    "kind": row["kind"],
                    "status": row["status"],
                    "progress": row["progress"],
                    "message": row["message"],
                    "payload": self._load_json(row["payload_json"], {}),
                    "result": self._load_json(row["result_json"], {}),
                    "error": row["error"],
                    "created_at": row["created_at"],
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                }
            )
            for row in rows
        ]

    def get_session_state(self) -> SessionInfo:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM session_state WHERE singleton_id = 1").fetchone()
        if not row:
            return SessionInfo()
        cookies = self._load_json(row["cookies_json"], [])
        return SessionInfo.model_validate(
            {
                "status": row["status"],
                "authenticated": row["status"] == "valid",
                "has_cookies": bool(cookies),
                "message": row["message"],
                "cookie_names": [cookie.get("name", "") for cookie in cookies if cookie.get("name")],
                "updated_at": row["updated_at"],
                "last_checked_at": row["last_checked_at"],
            }
        )

    def save_session_state(
        self, *, cookies: list[dict[str, Any]], status: str, message: str, last_checked_at: str | None = None
    ) -> SessionInfo:
        updated_at = utcnow_iso()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO session_state (
                    singleton_id, cookies_json, status, message, updated_at, last_checked_at
                ) VALUES (1, ?, ?, ?, ?, ?)
                """,
                (json.dumps(cookies, ensure_ascii=False), status, message, updated_at, last_checked_at),
            )
        return self.get_session_state()

    def clear_session_state(self) -> SessionInfo:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM session_state WHERE singleton_id = 1")
        return SessionInfo()

    def set_app_setting(self, key: str, value: str) -> None:
        with self.database.connect() as connection:
            connection.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))

    def get_app_settings(self) -> dict[str, str]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT key, value FROM app_settings ORDER BY key ASC").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def get_stats(self) -> StatsResponse:
        with self.database.connect() as connection:
            totals = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(
                        CASE WHEN EXISTS(
                            SELECT 1
                            FROM challenge_files f
                            WHERE f.challenge_id = challenges.challenge_id AND f.status = 'downloaded'
                        ) THEN 1 ELSE 0 END
                    ) AS downloaded,
                    SUM(CASE WHEN has_attachments = 1 THEN 1 ELSE 0 END) AS with_files
                FROM challenges
                """
            ).fetchone()
            category_rows = connection.execute(
                """
                SELECT COALESCE(category, 'unknown') AS category, COUNT(*) AS count
                FROM challenges
                GROUP BY COALESCE(category, 'unknown')
                ORDER BY count DESC
                """
            ).fetchall()
            difficulty_rows = connection.execute(
                """
                SELECT COALESCE(CAST(difficulty AS TEXT), 'unknown') AS difficulty_label, COUNT(*) AS count
                FROM challenges
                GROUP BY COALESCE(CAST(difficulty AS TEXT), 'unknown')
                ORDER BY CASE WHEN challenges.difficulty IS NULL THEN 999 ELSE challenges.difficulty END ASC
                """
            ).fetchall()

        return StatsResponse(
            challenges_total=int(totals["total"] or 0),
            challenges_downloaded=int(totals["downloaded"] or 0),
            challenges_with_files=int(totals["with_files"] or 0),
            categories={row["category"]: int(row["count"]) for row in category_rows},
            difficulties={row["difficulty_label"]: int(row["count"]) for row in difficulty_rows},
        )
