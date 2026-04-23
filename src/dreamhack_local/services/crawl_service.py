"""Challenge crawling and detail synchronization."""

from __future__ import annotations

from typing import Any, Callable

from dreamhack_local.config import AppSettings
from dreamhack_local.crawler.client import DreamhackClient
from dreamhack_local.crawler.parser import ParsedChallengeDetail, ParsedListingItem, parse_detail, parse_listing
from dreamhack_local.storage.repository import AppRepository, utcnow_iso
from dreamhack_local.utils.normalization import category_display_name, extract_challenge_id, slugify_title

ProgressCallback = Callable[[float, str, dict[str, Any] | None], None]


class CrawlService:
    """Fetches listings and detail pages and persists normalized results."""

    def __init__(
        self,
        settings: AppSettings,
        repository: AppRepository,
        client: DreamhackClient,
        workspace_service: Any,
        logger: Any,
    ):
        self.settings = settings
        self.repository = repository
        self.client = client
        self.workspace_service = workspace_service
        self.logger = logger

    def _merge_listing_and_detail(self, listing: ParsedListingItem, detail: ParsedChallengeDetail) -> dict[str, Any]:
        category = detail.category or listing.category
        difficulty = detail.difficulty if detail.difficulty is not None else listing.difficulty
        return {
            "challenge_id": listing.challenge_id,
            "title": detail.title or listing.title,
            "slug": slugify_title(detail.title or listing.title, fallback=str(listing.challenge_id)),
            "url": detail.url or listing.url,
            "category": category,
            "category_display": category_display_name(category),
            "difficulty": difficulty,
            "difficulty_label": str(difficulty) if difficulty is not None else None,
            "status": detail.status or listing.status,
            "author": detail.author or listing.author,
            "solvers": detail.solvers if detail.solvers is not None else listing.solvers,
            "description_text": detail.description_text,
            "description_html": detail.description_html,
            "has_attachments": bool(detail.downloads),
            "parse_warnings": sorted(set(listing.warnings + detail.warnings)),
            "last_error": None,
            "last_crawled_at": utcnow_iso(),
            "metadata": {"download_urls": [download.url for download in detail.downloads]},
        }

    def crawl_challenge(self, identifier: str, *, progress_cb: ProgressCallback | None = None) -> dict[str, Any]:
        challenge_id = extract_challenge_id(identifier)
        challenge = self.repository.resolve_challenge(identifier)
        if challenge_id is None and challenge:
            challenge_id = challenge.challenge_id
        if challenge_id is None:
            raise ValueError(f"Could not resolve challenge identifier: {identifier}")

        detail_html = self.client.fetch_challenge_html(challenge_id)
        detail = parse_detail(
            detail_html, challenge_id=challenge_id, url=f"{self.settings.base_url}/wargame/challenges/{challenge_id}"
        )
        listing = ParsedListingItem(
            challenge_id=challenge_id,
            title=detail.title or (challenge.title if challenge else f"challenge-{challenge_id}"),
            url=f"{self.settings.base_url}/wargame/challenges/{challenge_id}",
            category=challenge.category if challenge else detail.category,
            difficulty=challenge.difficulty if challenge else detail.difficulty,
            status=challenge.status if challenge else detail.status,
            author=challenge.author if challenge else detail.author,
            solvers=challenge.solvers if challenge else detail.solvers,
            warnings=[],
        )
        saved = self.repository.upsert_challenge(self._merge_listing_and_detail(listing, detail))
        folder = self.workspace_service.persist_challenge_artifacts(
            saved, files=self.repository.list_challenge_files(saved.challenge_id)
        )
        self.repository.upsert_challenge({"challenge_id": saved.challenge_id, "local_path": str(folder)})

        if progress_cb:
            progress_cb(1.0, f"Crawled challenge {saved.challenge_id}", {"challenge_id": saved.challenge_id})

        refreshed = self.repository.get_challenge(saved.challenge_id)
        return {
            "challenge": refreshed.model_dump(mode="json") if refreshed else saved.model_dump(mode="json"),
            "local_path": str(folder),
        }

    def sync(
        self,
        *,
        category: str | None = None,
        difficulty: int | None = None,
        status: str | None = None,
        max_pages: int | None = None,
        progress_cb: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        run_id = self.repository.create_crawl_run(
            mode="sync",
            filters={"category": category, "difficulty": difficulty, "status": status, "max_pages": max_pages},
        )
        pages_seen = 0
        challenges_seen = 0
        challenges_updated = 0
        warnings: list[str] = []
        seen_ids: set[int] = set()
        max_pages = max_pages or self.settings.max_listing_pages

        try:
            for page in range(1, max_pages + 1):
                html_text = self.client.fetch_listing_html(
                    category=category, difficulty=difficulty, status=status, page=page
                )
                items, parse_warnings = parse_listing(
                    html_text,
                    base_url=self.settings.base_url,
                    category_hint=category,
                    difficulty_hint=difficulty,
                    status_hint=status,
                )
                warnings.extend(parse_warnings)
                pages_seen += 1
                if not items:
                    break

                for item in items:
                    if item.challenge_id in seen_ids:
                        continue
                    seen_ids.add(item.challenge_id)
                    challenges_seen += 1
                    try:
                        detail_html = self.client.fetch_challenge_html(item.challenge_id)
                        detail = parse_detail(detail_html, challenge_id=item.challenge_id, url=item.url)
                        saved = self.repository.upsert_challenge(self._merge_listing_and_detail(item, detail))
                        folder = self.workspace_service.persist_challenge_artifacts(
                            saved, files=self.repository.list_challenge_files(saved.challenge_id)
                        )
                        self.repository.upsert_challenge(
                            {"challenge_id": saved.challenge_id, "local_path": str(folder)}
                        )
                        challenges_updated += 1
                    except Exception as exc:
                        self.repository.upsert_challenge(
                            {
                                "challenge_id": item.challenge_id,
                                "title": item.title,
                                "slug": slugify_title(item.title, fallback=str(item.challenge_id)),
                                "url": item.url,
                                "category": item.category,
                                "category_display": category_display_name(item.category),
                                "difficulty": item.difficulty,
                                "difficulty_label": str(item.difficulty) if item.difficulty is not None else None,
                                "status": item.status,
                                "author": item.author,
                                "solvers": item.solvers,
                                "parse_warnings": item.warnings,
                                "last_error": str(exc),
                                "last_crawled_at": utcnow_iso(),
                            }
                        )
                        warnings.append(f"Challenge {item.challenge_id}: {exc}")

                    if progress_cb:
                        progress = min(challenges_seen / max(challenges_seen + 1, 1), 0.99)
                        progress_cb(
                            progress,
                            f"Crawled {challenges_seen} challenges",
                            {"challenge_id": item.challenge_id, "page": page},
                        )

            summary = {
                "run_id": run_id,
                "pages_seen": pages_seen,
                "challenges_seen": challenges_seen,
                "challenges_updated": challenges_updated,
                "warnings": warnings,
            }
            self.repository.update_crawl_run(
                run_id,
                status="completed",
                pages_seen=pages_seen,
                challenges_seen=challenges_seen,
                challenges_updated=challenges_updated,
                error_count=len(warnings),
                summary_json=summary,
                finished_at=utcnow_iso(),
            )
            if progress_cb:
                progress_cb(1.0, "Crawl sync completed", summary)
            return summary
        except Exception as exc:
            self.repository.update_crawl_run(
                run_id,
                status="failed",
                pages_seen=pages_seen,
                challenges_seen=challenges_seen,
                challenges_updated=challenges_updated,
                error_count=len(warnings) + 1,
                summary_json={"warnings": warnings, "error": str(exc)},
                finished_at=utcnow_iso(),
            )
            raise
