"""Shared constants used across the local app."""

from __future__ import annotations

from typing import Final

ALLOWED_CATEGORIES: Final[tuple[str, ...]] = (
    "misc",
    "crypto",
    "web",
    "web3",
    "pwnable",
    "forensics",
    "reversing",
    "cloud",
)

CATEGORY_DISPLAY_NAMES: Final[dict[str, str]] = {
    "misc": "Misc",
    "crypto": "Cryptography",
    "web": "Web",
    "web3": "Web3",
    "pwnable": "Pwnable",
    "forensics": "Forensics",
    "reversing": "Reverse_Engineering",
    "cloud": "Cloud",
}

DISPLAY_NAME_TO_CATEGORY: Final[dict[str, str]] = {value.lower(): key for key, value in CATEGORY_DISPLAY_NAMES.items()}

VALID_DIFFICULTIES: Final[set[int]] = set(range(0, 11))
VALID_STATUSES: Final[tuple[str, ...]] = ("todo", "attempted", "solved")

LISTING_TITLE_SELECTORS: Final[tuple[str, ...]] = (
    ".challenge-title",
    ".problem-title",
    ".card-title",
    ".title",
    "h1",
    "h2",
    "h3",
    "h4",
)

LISTING_META_SELECTORS: Final[tuple[str, ...]] = (
    ".badge",
    ".tag",
    ".label",
    ".meta span",
    ".meta li",
    ".challenge-meta span",
    ".challenge-meta li",
    ".info span",
    ".info li",
    "[data-category]",
    "[data-difficulty]",
    "[data-status]",
    "[data-author]",
    "[data-solvers]",
)

DETAIL_DESCRIPTION_SELECTORS: Final[tuple[str, ...]] = (
    ".challenge-description",
    ".problem-description",
    ".problem-content",
    ".challenge-detail",
    ".challenge-text",
    ".markdown-body",
    "main article",
    "article",
)

DETAIL_META_SELECTORS: Final[tuple[str, ...]] = (
    ".challenge-meta span",
    ".challenge-meta li",
    ".problem-info span",
    ".problem-info li",
    ".badge",
    ".tag",
    ".label",
    "aside li",
)

DEFAULT_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

SESSION_VALID_MARKERS: Final[tuple[str, ...]] = (
    "logout",
    "/logout",
    "mypage",
    "my page",
    "profile",
    "로그아웃",
    "내 정보",
)

SESSION_INVALID_MARKERS: Final[tuple[str, ...]] = ("login", "sign in", "로그인")

TERMINAL_DOWNLOAD_HINTS: Final[tuple[str, ...]] = ("download", "attachment", "problem-file", "file")
