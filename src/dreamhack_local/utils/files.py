"""File and filename helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from dreamhack_local.utils.normalization import safe_fs_name

CONTENT_DISPOSITION_FILENAME_RE = re.compile(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?')

CONTENT_TYPE_EXTENSION = {
    "application/zip": ".zip",
    "application/x-tar": ".tar",
    "application/x-7z-compressed": ".7z",
    "application/gzip": ".gz",
    "application/x-gzip": ".gz",
    "application/pdf": ".pdf",
}


def sanitize_filename(name: str | None, fallback: str = "attachment.bin") -> str:
    candidate = safe_fs_name(name, fallback=fallback)
    return candidate if "." in candidate else fallback if "." in fallback else f"{candidate}.bin"


def infer_filename(response: requests.Response, source_url: str, fallback: str = "attachment.bin") -> str:
    header = response.headers.get("Content-Disposition", "")
    if header:
        match = CONTENT_DISPOSITION_FILENAME_RE.search(header)
        if match:
            filename = unquote(match.group(1).strip().strip('"'))
            return sanitize_filename(filename, fallback=fallback)

    parsed = urlparse(source_url)
    basename = os.path.basename(unquote(parsed.path))
    if basename and "." in basename:
        return sanitize_filename(basename, fallback=fallback)

    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    extension = CONTENT_TYPE_EXTENSION.get(content_type, ".bin")
    stem = os.path.basename(unquote(parsed.path)).strip() or Path(fallback).stem or "attachment"
    return sanitize_filename(f"{stem}{extension}", fallback=fallback)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
