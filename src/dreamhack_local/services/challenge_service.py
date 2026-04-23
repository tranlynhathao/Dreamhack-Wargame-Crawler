"""High-level challenge queries, migration, and validation helpers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from dreamhack_local.config import AppSettings, save_settings_override
from dreamhack_local.models.schemas import ChallengeRecord, DoctorIssue, DoctorReport, SettingsView
from dreamhack_local.storage.repository import AppRepository
from dreamhack_local.utils.normalization import (
    category_display_name,
    clean_text,
    normalize_category,
    normalize_difficulty,
    slugify_title,
)


class ChallengeService:
    """Orchestrates local challenge inventory operations."""

    def __init__(
        self,
        settings: AppSettings,
        repository: AppRepository,
        workspace_service: Any,
        manifest_service: Any,
        session_service: Any,
        logger: Any,
    ):
        self.settings = settings
        self.repository = repository
        self.workspace_service = workspace_service
        self.manifest_service = manifest_service
        self.session_service = session_service
        self.logger = logger

    def bootstrap_from_manifest(self, manifest_path: Path | None = None) -> int:
        manifest_path = manifest_path or self.settings.manifest_export_path
        if not manifest_path.exists():
            return 0
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return 0

        imported = 0
        for key, entry in payload.items():
            title = clean_text(entry.get("title"))
            if not title:
                continue

            warnings: list[str] = []
            category = normalize_category(entry.get("category"))
            if entry.get("category") and category is None:
                warnings.append(f"Invalid legacy category ignored: {entry.get('category')}")
            difficulty = normalize_difficulty(entry.get("difficulty"))
            if entry.get("difficulty") not in (None, "") and difficulty is None:
                warnings.append(f"Invalid legacy difficulty ignored: {entry.get('difficulty')}")

            self.repository.upsert_challenge(
                {
                    "challenge_id": int(entry.get("id") or key),
                    "title": title,
                    "slug": slugify_title(title, fallback=str(entry.get("id") or key)),
                    "url": entry.get("challenge_url") or "",
                    "category": category,
                    "category_display": category_display_name(category),
                    "difficulty": difficulty,
                    "difficulty_label": str(difficulty) if difficulty is not None else None,
                    "downloaded": bool(entry.get("has_download", False)),
                    "description_text": clean_text(entry.get("description")),
                    "parse_warnings": warnings,
                    "first_seen": entry.get("first_seen"),
                    "last_seen": entry.get("last_seen") or entry.get("first_seen"),
                }
            )
            imported += 1
        return imported

    def list_challenges(self, **filters: Any) -> list[ChallengeRecord]:
        return self.repository.list_challenges(**filters)

    def get_challenge(self, identifier: str) -> ChallengeRecord | None:
        resolved = self.repository.resolve_challenge(identifier)
        if resolved:
            return resolved
        return None

    def sync_files(self) -> dict[str, int]:
        return self.workspace_service.sync_from_disk()

    def export_manifest(
        self, *, output_path: Path | None = None, sort_by: str = "id", sort_order: str = "desc"
    ) -> Path:
        return self.manifest_service.export(output_path=output_path, sort_by=sort_by, sort_order=sort_order)

    def doctor(self) -> DoctorReport:
        report = DoctorReport()
        challenges = self.repository.list_challenges(limit=1_000_000)

        for challenge in challenges:
            if challenge.local_path:
                path = Path(challenge.local_path)
                if not path.exists():
                    report.issues.append(
                        DoctorIssue(
                            severity="error",
                            code="missing-local-path",
                            message=f"Local path is recorded but missing on disk: {path}",
                            challenge_id=challenge.challenge_id,
                            path=str(path),
                        )
                    )
            if challenge.downloaded and not challenge.local_path:
                report.issues.append(
                    DoctorIssue(
                        severity="warning",
                        code="downloaded-without-path",
                        message="Challenge is marked downloaded but has no local path.",
                        challenge_id=challenge.challenge_id,
                    )
                )
            if challenge.has_attachments and challenge.downloaded and challenge.file_count == 0:
                report.issues.append(
                    DoctorIssue(
                        severity="warning",
                        code="missing-file-records",
                        message="Challenge has attachments and is marked downloaded, but no downloaded file records exist.",
                        challenge_id=challenge.challenge_id,
                    )
                )

        session_status = self.session_service.get_status()
        if session_status.status == "missing":
            report.issues.append(
                DoctorIssue(severity="info", code="missing-session", message="No stored DreamHack session was found.")
            )

        return report

    def open_folder(self, *, challenge_id: str | None = None, path: str | None = None) -> Path:
        target: Path | None = None

        if challenge_id:
            challenge = self.get_challenge(challenge_id)
            if challenge is None:
                raise ValueError(f"Challenge {challenge_id} was not found.")
            if challenge.local_path:
                target = Path(challenge.local_path)
            else:
                folder = self.workspace_service.ensure_challenge_folder(challenge)
                self.repository.upsert_challenge({"challenge_id": challenge.challenge_id, "local_path": str(folder)})
                target = folder
        elif path:
            candidate = Path(path).expanduser().resolve()
            workspace_root = self.settings.workspace_root.resolve()
            try:
                candidate.relative_to(workspace_root)
            except ValueError as exc:
                raise ValueError("Only paths inside the configured workspace can be opened.") from exc
            target = candidate

        if target is None:
            raise ValueError("Provide challenge_id or path.")
        if not target.exists():
            raise ValueError(f"Path does not exist: {target}")

        if sys.platform == "darwin":
            command = ["open", str(target)]
        elif os.name == "nt":
            command = ["cmd", "/c", "start", "", str(target)]
        else:
            command = ["xdg-open", str(target)]

        try:
            subprocess.Popen(command)
        except OSError as exc:
            raise ValueError(f"Could not open folder: {exc}") from exc

        self.logger.info("Opened local path %s", target)
        return target

    def get_settings_view(self) -> SettingsView:
        return SettingsView(
            base_url=self.settings.base_url,
            workspace_root=str(self.settings.workspace_root),
            database_path=str(self.settings.database_path),
            manifest_export_path=str(self.settings.manifest_export_path),
            request_delay_seconds=self.settings.request_delay_seconds,
            max_retries=self.settings.max_retries,
            timeout_seconds=self.settings.timeout_seconds,
            log_level=self.settings.log_level,
        )

    def update_settings(self, **updates: Any) -> SettingsView:
        filtered = {key: value for key, value in updates.items() if value is not None}
        if not filtered:
            return self.get_settings_view()
        if "workspace_root" in filtered:
            filtered["workspace_root"] = str(Path(filtered["workspace_root"]).expanduser().resolve())
        settings = save_settings_override(**filtered)
        self.repository.set_app_setting("workspace_root", str(settings.workspace_root))
        self.repository.set_app_setting("request_delay_seconds", str(settings.request_delay_seconds))
        return SettingsView(
            base_url=settings.base_url,
            workspace_root=str(settings.workspace_root),
            database_path=str(settings.database_path),
            manifest_export_path=str(settings.manifest_export_path),
            request_delay_seconds=settings.request_delay_seconds,
            max_retries=settings.max_retries,
            timeout_seconds=settings.timeout_seconds,
            log_level=settings.log_level,
        )
