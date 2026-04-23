"""Pydantic models used by the service, CLI, and API layers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChallengeFileRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    challenge_id: int
    filename: str
    relative_path: str
    source_url: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    status: str = "downloaded"
    last_error: str | None = None
    downloaded_at: datetime | None = None


class ChallengeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    challenge_id: int
    title: str
    slug: str
    url: str
    category: str | None = None
    category_display: str | None = None
    difficulty: int | None = None
    difficulty_label: str | None = None
    status: str | None = None
    author: str | None = None
    solvers: int | None = None
    has_attachments: bool = False
    downloaded: bool = False
    local_path: str | None = None
    description_text: str | None = None
    description_html: str | None = None
    download_status: str = "not_downloaded"
    parse_warnings: list[str] = Field(default_factory=list)
    last_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    last_crawled_at: datetime | None = None
    last_downloaded_at: datetime | None = None
    file_count: int = 0
    byte_count: int = 0


class ChallengeDetailResponse(BaseModel):
    challenge: ChallengeRecord
    files: list[ChallengeFileRecord] = Field(default_factory=list)


class SessionInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["missing", "valid", "invalid", "unknown"] = "missing"
    authenticated: bool = False
    has_cookies: bool = False
    message: str = ""
    cookie_names: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None
    last_checked_at: datetime | None = None


class JobRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str
    kind: str
    status: str
    progress: float = 0.0
    message: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class StatsResponse(BaseModel):
    challenges_total: int = 0
    challenges_downloaded: int = 0
    challenges_with_files: int = 0
    categories: dict[str, int] = Field(default_factory=dict)
    difficulties: dict[str, int] = Field(default_factory=dict)


class SettingsView(BaseModel):
    base_url: str
    workspace_root: str
    database_path: str
    manifest_export_path: str
    request_delay_seconds: float
    max_retries: int
    timeout_seconds: float
    log_level: str


class DoctorIssue(BaseModel):
    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    challenge_id: int | None = None
    path: str | None = None


class DoctorReport(BaseModel):
    issues: list[DoctorIssue] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")


class SessionImportRequest(BaseModel):
    cookie_header: str | None = None
    cookie_file: str | None = None


class OpenFolderRequest(BaseModel):
    challenge_id: str | None = None
    path: str | None = None


class OpenFolderResponse(BaseModel):
    path: str


class CrawlSyncRequest(BaseModel):
    category: str | None = None
    difficulty: int | None = None
    status: str | None = None
    max_pages: int | None = None


class CrawlChallengeRequest(BaseModel):
    identifier: str


class BulkDownloadRequest(BaseModel):
    category: str | None = None
    difficulty: int | None = None
    status: str | None = None
    downloaded: bool | None = None
    search: str | None = None
    mode: Literal["skip", "overwrite", "resume"] = "resume"


class SettingsUpdateRequest(BaseModel):
    workspace_root: str | None = None
    request_delay_seconds: float | None = None
    max_retries: int | None = None
    timeout_seconds: float | None = None
    log_level: str | None = None
