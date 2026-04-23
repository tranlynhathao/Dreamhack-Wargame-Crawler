"""Workspace path helpers."""

from __future__ import annotations

from pathlib import Path

from dreamhack_local.utils.normalization import category_display_name, difficulty_folder_name, safe_fs_name


def challenge_workspace_path(
    workspace_root: Path, *, category: str | None, difficulty: int | None, title: str | None, challenge_id: int
) -> Path:
    challenge_name = safe_fs_name(title, fallback=str(challenge_id))
    return workspace_root / category_display_name(category) / difficulty_folder_name(difficulty) / challenge_name
