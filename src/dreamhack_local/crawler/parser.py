"""HTML parsing for listings and challenge detail pages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from dreamhack_local.core.constants import (
    DETAIL_DESCRIPTION_SELECTORS,
    DETAIL_META_SELECTORS,
    LISTING_META_SELECTORS,
    LISTING_TITLE_SELECTORS,
    TERMINAL_DOWNLOAD_HINTS,
)
from dreamhack_local.utils.normalization import (
    clean_text,
    extract_small_integers,
    html_to_markdownish,
    normalize_category,
    normalize_difficulty,
    normalize_status,
)

CHALLENGE_URL_RE = re.compile(r"/wargame/challenges/(\d+)")


@dataclass(slots=True)
class ParsedDownload:
    url: str
    label: str | None = None


@dataclass(slots=True)
class ParsedListingItem:
    challenge_id: int
    title: str
    url: str
    category: str | None = None
    difficulty: int | None = None
    status: str | None = None
    author: str | None = None
    solvers: int | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ParsedChallengeDetail:
    challenge_id: int
    title: str | None = None
    url: str | None = None
    category: str | None = None
    difficulty: int | None = None
    status: str | None = None
    author: str | None = None
    solvers: int | None = None
    description_html: str | None = None
    description_text: str | None = None
    downloads: list[ParsedDownload] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _anchor_candidates(soup: BeautifulSoup) -> list[Tag]:
    return [anchor for anchor in soup.find_all("a", href=True) if CHALLENGE_URL_RE.search(anchor.get("href", ""))]


def _candidate_card(anchor: Tag) -> Tag:
    current: Tag | None = anchor
    for _ in range(6):
        if current is None:
            break
        if current.name in {"article", "li", "tr"}:
            return current
        classes = " ".join(current.get("class", []))
        if any(token in classes for token in ("challenge", "problem", "card", "row", "item")):
            return current
        current = current.parent if isinstance(current.parent, Tag) else None
    return anchor


def _collect_meta_texts(container: Tag, selectors: tuple[str, ...]) -> list[str]:
    seen: list[str] = []
    for selector in selectors:
        for node in container.select(selector):
            if not isinstance(node, Tag):
                continue
            text = clean_text(
                node.get("data-category") or node.get("data-difficulty") or node.get_text(" ", strip=True)
            )
            if text and len(text) <= 64 and text not in seen:
                seen.append(text)
    return seen


def _extract_author(container: Tag, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        for node in container.select(selector):
            if not isinstance(node, Tag):
                continue
            data_author = clean_text(node.get("data-author"))
            if data_author:
                return data_author
            candidate = clean_text(node.get_text(" ", strip=True))
            if not candidate:
                continue
            lowered = candidate.lower()
            if lowered.startswith("author"):
                parts = candidate.split(":", 1)
                return clean_text(parts[1] if len(parts) == 2 else candidate)
            if "author" in lowered:
                return candidate
    return None


def _extract_solvers(texts: list[str]) -> int | None:
    scoped = [text for text in texts if "solver" in text.lower() or "solved" in text.lower()]
    return extract_small_integers(scoped, upper_bound=10_000_000)


def parse_listing(
    html_text: str,
    *,
    base_url: str,
    category_hint: str | None = None,
    difficulty_hint: int | None = None,
    status_hint: str | None = None,
) -> tuple[list[ParsedListingItem], list[str]]:
    soup = BeautifulSoup(html_text, "lxml")
    warnings: list[str] = []
    seen_ids: set[int] = set()
    results: list[ParsedListingItem] = []

    for anchor in _anchor_candidates(soup):
        href = anchor.get("href", "")
        match = CHALLENGE_URL_RE.search(href)
        if not match:
            continue
        challenge_id = int(match.group(1))
        if challenge_id in seen_ids:
            continue
        seen_ids.add(challenge_id)

        card = _candidate_card(anchor)
        title = clean_text(anchor.get_text(" ", strip=True))
        if not title:
            for selector in LISTING_TITLE_SELECTORS:
                title_node = card.select_one(selector)
                if isinstance(title_node, Tag):
                    title = clean_text(title_node.get_text(" ", strip=True))
                    if title:
                        break
        if not title:
            warnings.append(f"Challenge {challenge_id} skipped because no title was found")
            continue

        meta_texts = _collect_meta_texts(card, LISTING_META_SELECTORS)
        category = normalize_category(category_hint)
        difficulty = normalize_difficulty(difficulty_hint)
        status = normalize_status(status_hint)

        if category is None:
            for text in meta_texts:
                parsed = normalize_category(text)
                if parsed is not None:
                    category = parsed
                    break

        if difficulty is None:
            for text in meta_texts:
                parsed = normalize_difficulty(text)
                if parsed is not None:
                    difficulty = parsed
                    break

        if status is None:
            for text in meta_texts:
                parsed = normalize_status(text)
                if parsed is not None:
                    status = parsed
                    break

        item_warnings: list[str] = []
        if category_hint is None and category is None:
            item_warnings.append("Category unavailable from listing")
        if difficulty_hint is None and difficulty is None:
            item_warnings.append("Difficulty unavailable from listing")

        results.append(
            ParsedListingItem(
                challenge_id=challenge_id,
                title=title,
                url=urljoin(base_url, href),
                category=category,
                difficulty=difficulty,
                status=status,
                author=_extract_author(card, LISTING_META_SELECTORS),
                solvers=_extract_solvers(meta_texts),
                warnings=item_warnings,
            )
        )

    return results, warnings


def parse_detail(html_text: str, *, challenge_id: int, url: str) -> ParsedChallengeDetail:
    soup = BeautifulSoup(html_text, "lxml")
    warnings: list[str] = []

    title = None
    for selector in LISTING_TITLE_SELECTORS:
        title_node = soup.select_one(selector)
        if isinstance(title_node, Tag):
            title = clean_text(title_node.get_text(" ", strip=True))
            if title:
                break

    description_html = None
    for selector in DETAIL_DESCRIPTION_SELECTORS:
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            description_html = str(node)
            break

    meta_texts = _collect_meta_texts(soup, DETAIL_META_SELECTORS)
    category = None
    difficulty = None
    status = None

    for text in meta_texts:
        if category is None:
            category = normalize_category(text)
        if difficulty is None:
            difficulty = normalize_difficulty(text)
        if status is None:
            status = normalize_status(text)

    downloads: list[ParsedDownload] = []
    seen_downloads: set[str] = set()
    for node in soup.find_all(["a", "button"], href=True):
        href = node.get("href")
        if not href:
            continue
        lowered = href.lower()
        if href.startswith("#"):
            continue
        if not href.startswith("http"):
            absolute_url = urljoin(url, href)
        else:
            absolute_url = href
        if any(token in lowered for token in TERMINAL_DOWNLOAD_HINTS) or ".s3.amazonaws.com" in lowered:
            if absolute_url not in seen_downloads:
                downloads.append(
                    ParsedDownload(url=absolute_url, label=clean_text(node.get_text(" ", strip=True)) or None)
                )
                seen_downloads.add(absolute_url)

    for node in soup.find_all(attrs={"data-href": True}):
        href = clean_text(str(node.get("data-href")))
        if not href:
            continue
        absolute_url = urljoin(url, href)
        lowered = absolute_url.lower()
        if any(token in lowered for token in TERMINAL_DOWNLOAD_HINTS) or ".s3.amazonaws.com" in lowered:
            if absolute_url not in seen_downloads:
                downloads.append(ParsedDownload(url=absolute_url))
                seen_downloads.add(absolute_url)

    if description_html is None:
        warnings.append("Description unavailable from detail page")

    return ParsedChallengeDetail(
        challenge_id=challenge_id,
        title=title,
        url=url,
        category=category,
        difficulty=difficulty,
        status=status,
        author=_extract_author(soup, DETAIL_META_SELECTORS),
        solvers=_extract_solvers(meta_texts),
        description_html=description_html,
        description_text=html_to_markdownish(description_html),
        downloads=downloads,
        warnings=warnings,
    )
