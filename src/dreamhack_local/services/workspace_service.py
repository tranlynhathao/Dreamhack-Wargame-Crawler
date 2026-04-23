"""Workspace layout and file synchronization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dreamhack_local.config import AppSettings
from dreamhack_local.core.constants import CATEGORY_DISPLAY_NAMES
from dreamhack_local.models.schemas import ChallengeFileRecord, ChallengeRecord
from dreamhack_local.storage.repository import AppRepository
from dreamhack_local.utils.files import write_json, write_text
from dreamhack_local.utils.normalization import (
    category_display_name,
    difficulty_folder_name,
    normalize_category,
    normalize_difficulty,
    safe_fs_name,
    slugify_title,
)
from dreamhack_local.utils.paths import challenge_workspace_path


class WorkspaceService:
    """Owns the on-disk folder layout for local challenge data."""

    def __init__(self, settings: AppSettings, repository: AppRepository, logger: Any):
        self.settings = settings
        self.repository = repository
        self.logger = logger

    def _find_existing_folder(self, challenge: ChallengeRecord) -> Path | None:
        if challenge.local_path:
            path = Path(challenge.local_path)
            if path.exists():
                return path

        base_dir = (
            self.settings.workspace_root
            / category_display_name(challenge.category)
            / difficulty_folder_name(challenge.difficulty)
        )
        if not base_dir.exists():
            return None

        target_name = safe_fs_name(challenge.title, fallback=str(challenge.challenge_id))
        target_slug = slugify_title(target_name, fallback=str(challenge.challenge_id))
        exact = base_dir / target_name
        if exact.exists():
            return exact

        for candidate in base_dir.iterdir():
            if not candidate.is_dir():
                continue
            if slugify_title(candidate.name, fallback="") == target_slug:
                return candidate
        return None

    def ensure_challenge_folder(self, challenge: ChallengeRecord) -> Path:
        existing = self._find_existing_folder(challenge)
        if existing:
            return existing
        path = challenge_workspace_path(
            self.settings.workspace_root,
            category=challenge.category,
            difficulty=challenge.difficulty,
            title=challenge.title,
            challenge_id=challenge.challenge_id,
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    def persist_challenge_artifacts(
        self, challenge: ChallengeRecord, *, files: list[ChallengeFileRecord] | None = None
    ) -> Path:
        folder = self.ensure_challenge_folder(challenge)
        write_text(folder / "description.md", challenge.description_text or "")
        if challenge.description_html:
            write_text(folder / "description.html", challenge.description_html)

        payload = challenge.model_dump(mode="json")
        payload["files"] = [file.model_dump(mode="json") for file in (files or [])]
        write_json(folder / "metadata.json", payload)
        (folder / "files").mkdir(parents=True, exist_ok=True)
        return folder

    def sync_from_disk(self) -> dict[str, int]:
        updated = 0
        matched = 0
        scanned = 0

        for category_dir in self.settings.workspace_root.iterdir():
            if not category_dir.is_dir():
                continue
            category = normalize_category(category_dir.name)
            if category is None and category_dir.name.lower() not in {
                value.lower() for value in CATEGORY_DISPLAY_NAMES.values()
            }:
                continue

            for level_dir in category_dir.iterdir():
                if not level_dir.is_dir() or not level_dir.name.startswith("Level_"):
                    continue
                difficulty = normalize_difficulty(level_dir.name)

                for challenge_dir in level_dir.iterdir():
                    if not challenge_dir.is_dir():
                        continue
                    scanned += 1
                    metadata_path = challenge_dir / "metadata.json"
                    challenge = None

                    if metadata_path.exists():
                        try:
                            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                            challenge_id = metadata.get("challenge_id") or metadata.get("id")
                            if challenge_id:
                                challenge = self.repository.get_challenge(int(challenge_id))
                        except (json.JSONDecodeError, OSError, ValueError):
                            challenge = None

                    if challenge is None:
                        title_guess = challenge_dir.name.replace("_", " ")
                        candidates = self.repository.list_challenges(
                            category=category, difficulty=difficulty, search=title_guess, limit=20
                        )
                        target_slug = slugify_title(challenge_dir.name)
                        for candidate in candidates:
                            if slugify_title(candidate.title) == target_slug:
                                challenge = candidate
                                break

                    if challenge is None:
                        continue

                    files_dir = challenge_dir / "files"
                    has_local_content = any(
                        path.name not in {"metadata.json", "description.md", "description.html"}
                        for path in challenge_dir.iterdir()
                    )
                    if files_dir.exists():
                        has_local_content = has_local_content or any(files_dir.iterdir())

                    matched += 1
                    saved = self.repository.upsert_challenge(
                        {
                            "challenge_id": challenge.challenge_id,
                            "category": challenge.category or category,
                            "category_display": category_display_name(challenge.category or category),
                            "difficulty": challenge.difficulty if challenge.difficulty is not None else difficulty,
                            "difficulty_label": str(
                                challenge.difficulty if challenge.difficulty is not None else difficulty
                            )
                            if (challenge.difficulty is not None or difficulty is not None)
                            else None,
                            "local_path": str(challenge_dir),
                            "downloaded": has_local_content or challenge.downloaded,
                        }
                    )
                    updated += 1 if saved else 0

        return {"scanned": scanned, "matched": matched, "updated": updated}
