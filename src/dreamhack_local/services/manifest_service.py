"""Compatibility export back to manifest.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dreamhack_local.config import AppSettings
from dreamhack_local.storage.repository import AppRepository


class ManifestService:
    """Exports the SQLite source of truth to the legacy manifest format."""

    def __init__(self, settings: AppSettings, repository: AppRepository, logger: Any):
        self.settings = settings
        self.repository = repository
        self.logger = logger

    def export(self, *, output_path: Path | None = None, sort_by: str = "id", sort_order: str = "desc") -> Path:
        records = self.repository.list_challenges(limit=1_000_000)
        payload: dict[str, dict[str, Any]] = {}

        for record in records:
            payload[str(record.challenge_id)] = {
                "id": str(record.challenge_id),
                "title": record.title,
                "challenge_url": record.url,
                "category": record.category or "",
                "difficulty": "" if record.difficulty is None else str(record.difficulty),
                "has_download": bool(record.downloaded),
                "description": record.description_text or "",
                "first_seen": record.first_seen.isoformat() if record.first_seen else None,
                "last_seen": record.last_seen.isoformat() if record.last_seen else None,
            }

        if sort_by != "none":
            payload = self._sort(payload, sort_by=sort_by, sort_order=sort_order)

        output_path = output_path or self.settings.manifest_export_path
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def _sort(self, payload: dict[str, dict[str, Any]], *, sort_by: str, sort_order: str) -> dict[str, dict[str, Any]]:
        reverse = sort_order == "desc"
        items = list(payload.items())

        if sort_by == "id":
            items.sort(key=lambda item: int(item[0]), reverse=reverse)
        elif sort_by == "title":
            items.sort(key=lambda item: item[1]["title"].lower(), reverse=reverse)
        elif sort_by == "category":
            items.sort(key=lambda item: ((item[1]["category"] or "").lower(), int(item[0])), reverse=reverse)
        elif sort_by == "difficulty":
            items.sort(key=lambda item: (int(item[1]["difficulty"] or -1), int(item[0])), reverse=reverse)
        elif sort_by == "first_seen":
            items.sort(key=lambda item: item[1]["first_seen"] or "", reverse=reverse)
        elif sort_by == "last_seen":
            items.sort(key=lambda item: item[1]["last_seen"] or "", reverse=reverse)
        elif sort_by == "has_download":
            items.sort(key=lambda item: (bool(item[1]["has_download"]), int(item[0])), reverse=reverse)
        else:
            items.sort(key=lambda item: int(item[0]), reverse=reverse)

        return dict(items)
