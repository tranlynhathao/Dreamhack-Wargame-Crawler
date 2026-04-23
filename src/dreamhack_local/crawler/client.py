"""Authenticated HTTP client with local session persistence."""

from __future__ import annotations

import threading
import time
from typing import Any
from urllib.parse import urljoin

import requests

from dreamhack_local.config import AppSettings
from dreamhack_local.core.constants import DEFAULT_HEADERS, SESSION_INVALID_MARKERS, SESSION_VALID_MARKERS
from dreamhack_local.core.exceptions import AccessDeniedError, SessionError
from dreamhack_local.models.schemas import SessionInfo


class DreamhackClient:
    """Single authenticated requests.Session abstraction."""

    def __init__(self, settings: AppSettings, session_service: Any, logger: Any):
        self.settings = settings
        self.session_service = session_service
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.session_service.apply_to_session(self.session)
        self._rate_lock = threading.Lock()
        self._last_request_at = 0.0

    def refresh_session(self) -> None:
        self.session.cookies.clear()
        self.session_service.apply_to_session(self.session)

    @staticmethod
    def _looks_logged_out(content: str) -> bool:
        lowered = content.lower()
        invalid_markers = any(marker in lowered for marker in SESSION_INVALID_MARKERS)
        valid_markers = any(marker in lowered for marker in SESSION_VALID_MARKERS)
        return invalid_markers and not valid_markers

    def _wait_for_rate_limit(self) -> None:
        with self._rate_lock:
            elapsed = time.monotonic() - self._last_request_at
            remaining = self.settings.request_delay_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._last_request_at = time.monotonic()

    def request(
        self,
        method: str,
        url: str,
        *,
        authenticated: bool = True,
        stream: bool = False,
        expected_statuses: tuple[int, ...] = (200,),
        **kwargs: Any,
    ) -> requests.Response:
        if authenticated and not self.session.cookies:
            raise SessionError("No authenticated session is configured. Import cookies first.")

        last_error: Exception | None = None
        for attempt in range(1, self.settings.max_retries + 1):
            self._wait_for_rate_limit()
            try:
                response = self.session.request(
                    method, url, timeout=self.settings.timeout_seconds, stream=stream, **kwargs
                )
                self.logger.debug("HTTP %s %s -> %s", method, response.url, response.status_code)
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.settings.max_retries:
                    raise
                time.sleep(self.settings.request_delay_seconds * (2 ** (attempt - 1)))
                continue

            if response.status_code in {401, 403}:
                raise AccessDeniedError(
                    f"Access denied for {url} with status {response.status_code}. "
                    "The current session is not authorized for this resource."
                )

            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt >= self.settings.max_retries:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                sleep_for = (
                    float(retry_after)
                    if retry_after and retry_after.isdigit()
                    else self.settings.request_delay_seconds * (2 ** (attempt - 1))
                )
                time.sleep(sleep_for)
                continue

            if expected_statuses and response.status_code not in expected_statuses:
                response.raise_for_status()
            return response

        if last_error:
            raise last_error
        raise RuntimeError(f"Request failed unexpectedly for {url}")

    def build_listing_url(
        self, *, category: str | None = None, difficulty: int | None = None, status: str | None = None, page: int = 1
    ) -> str:
        params: dict[str, str] = {}
        if category:
            params["category"] = category
        if difficulty is not None:
            params["difficulty"] = str(difficulty)
        if status:
            params["status"] = status
        if page > 1:
            params["page"] = str(page)

        base = self.settings.wargame_url
        if not params:
            return base
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{base}?{query}"

    def fetch_listing_html(
        self, *, category: str | None = None, difficulty: int | None = None, status: str | None = None, page: int = 1
    ) -> str:
        response = self.request(
            "GET",
            self.build_listing_url(category=category, difficulty=difficulty, status=status, page=page),
            authenticated=False,
        )
        return response.text

    def fetch_challenge_html(self, challenge_id: int) -> str:
        expected_url = urljoin(self.settings.base_url, f"/wargame/challenges/{challenge_id}")
        response = self.request("GET", expected_url)
        content = response.text
        final_url = response.url.lower()
        if any(token in final_url for token in ("/login", "/signin", "/accounts")):
            raise AccessDeniedError(
                f"Challenge {challenge_id} redirected to a login page. The current session is not authorized."
            )
        if self._looks_logged_out(content):
            raise AccessDeniedError(
                f"Challenge {challenge_id} returned a logged-out page. Refresh the local session and try again."
            )
        return content

    def validate_download_response(self, response: requests.Response, *, source_url: str, first_chunk: bytes) -> None:
        final_url = response.url.lower()
        if any(token in final_url for token in ("/login", "/signin", "/accounts")):
            raise AccessDeniedError(
                f"Download {source_url} redirected to a login page. The current session is not authorized."
            )

        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        content_disposition = response.headers.get("Content-Disposition", "").lower()
        if content_type not in {"text/html", "application/xhtml+xml", "application/json"}:
            return
        if "attachment" in content_disposition:
            return

        preview = first_chunk[:8192].decode("utf-8", errors="ignore").lower()
        if self._looks_logged_out(preview) or ("<html" in preview and "dreamhack" in preview):
            raise AccessDeniedError(
                f"Download {source_url} returned an HTML page instead of a file. "
                "The session may be invalid or the challenge file is not accessible."
            )
        if content_type == "application/json" and ("error" in preview or "message" in preview):
            raise AccessDeniedError(f"Download {source_url} returned a JSON error payload instead of a file.")

    def inspect_session(self) -> SessionInfo:
        self.refresh_session()
        if not self.session.cookies:
            return SessionInfo(
                status="missing", authenticated=False, has_cookies=False, message="No stored cookies found."
            )

        response = self.request("GET", self.settings.base_url, authenticated=False)
        content = response.text.lower()
        valid_markers = any(marker in content for marker in SESSION_VALID_MARKERS)
        invalid_markers = any(marker in content for marker in SESSION_INVALID_MARKERS)

        if valid_markers:
            return SessionInfo(
                status="valid",
                authenticated=True,
                has_cookies=True,
                message="Session looks authenticated.",
                cookie_names=list(self.session.cookies.keys()),
            )
        if invalid_markers:
            return SessionInfo(
                status="invalid",
                authenticated=False,
                has_cookies=True,
                message="Session cookies are present but the homepage looks logged out.",
                cookie_names=list(self.session.cookies.keys()),
            )
        return SessionInfo(
            status="unknown",
            authenticated=False,
            has_cookies=True,
            message="Session cookies are present but login state could not be confirmed heuristically.",
            cookie_names=list(self.session.cookies.keys()),
        )
