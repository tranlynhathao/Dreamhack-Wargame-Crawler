"""Normalization and text helpers."""

from __future__ import annotations

import html
import re
import unicodedata
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from dreamhack_local.core.constants import (
    ALLOWED_CATEGORIES,
    CATEGORY_DISPLAY_NAMES,
    DISPLAY_NAME_TO_CATEGORY,
    VALID_DIFFICULTIES,
    VALID_STATUSES,
)

INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
SLUG_RE = re.compile(r"[^a-z0-9]+")
MULTISPACE_RE = re.compile(r"\s+")
CHALLENGE_ID_RE = re.compile(r"/wargame/challenges/(\d+)")

CATEGORY_ALIASES = {
    "cryptography": "crypto",
    "crypto": "crypto",
    "web": "web",
    "web3": "web3",
    "pwn": "pwnable",
    "pwnable": "pwnable",
    "reversing": "reversing",
    "reverse engineering": "reversing",
    "reverse_engineering": "reversing",
    "rev": "reversing",
    "misc": "misc",
    "forensics": "forensics",
    "cloud": "cloud",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return MULTISPACE_RE.sub(" ", html.unescape(value)).strip()


def normalize_category(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = clean_text(value).lower().replace("-", " ").replace("_", " ")
    normalized = CATEGORY_ALIASES.get(normalized, DISPLAY_NAME_TO_CATEGORY.get(normalized, normalized))
    if normalized in ALLOWED_CATEGORIES:
        return normalized
    return None


def category_display_name(category: str | None) -> str:
    normalized = normalize_category(category)
    if normalized:
        return CATEGORY_DISPLAY_NAMES[normalized]
    return "Uncategorized"


def normalize_difficulty(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value in VALID_DIFFICULTIES else None

    text = clean_text(str(value)).lower()
    if not text:
        return None
    if text == "beginner":
        return 0
    match = re.search(r"(?:level\s*)?(\d+)", text)
    if not match:
        return None
    try:
        parsed = int(match.group(1))
    except ValueError:
        return None
    return parsed if parsed in VALID_DIFFICULTIES else None


def difficulty_folder_name(difficulty: int | None) -> str:
    return f"Level_{difficulty}" if difficulty is not None else "Level_Unknown"


def difficulty_label(difficulty: int | None) -> str | None:
    return None if difficulty is None else str(difficulty)


def normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = clean_text(value).lower()
    return normalized if normalized in VALID_STATUSES else None


def safe_fs_name(value: str | None, fallback: str = "challenge") -> str:
    text = unicodedata.normalize("NFKC", clean_text(value))
    text = INVALID_FS_CHARS.sub("_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.strip("._")
    return text or fallback


def slugify_title(title: str | None, fallback: str = "challenge") -> str:
    text = unicodedata.normalize("NFKC", clean_text(title)).lower()
    text = SLUG_RE.sub("-", text)
    text = text.strip("-")
    return text or fallback


def extract_challenge_id(identifier: str) -> int | None:
    identifier = identifier.strip()
    if identifier.isdigit():
        return int(identifier)
    match = CHALLENGE_ID_RE.search(identifier)
    if match:
        return int(match.group(1))
    try:
        parsed = urlparse(identifier)
        if parsed.path:
            match = CHALLENGE_ID_RE.search(parsed.path)
            if match:
                return int(match.group(1))
    except ValueError:
        return None
    return None


def html_to_markdownish(html_text: str | None) -> str:
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "section", "article", "li", "ul", "ol", "h1", "h2", "h3", "h4"]):
        block.append("\n")
    text = soup.get_text(" ", strip=True)
    text = html.unescape(text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def extract_small_integers(texts: list[str], upper_bound: int = 1_000_000) -> int | None:
    for text in texts:
        match = re.search(r"(\d[\d,]*)", text)
        if not match:
            continue
        value = int(match.group(1).replace(",", ""))
        if value <= upper_bound:
            return value
    return None
