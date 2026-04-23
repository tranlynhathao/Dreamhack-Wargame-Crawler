"""Local session persistence and import helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from dreamhack_local.config import AppSettings
from dreamhack_local.models.schemas import SessionInfo
from dreamhack_local.storage.repository import AppRepository, utcnow_iso


class SessionService:
    """Persists DreamHack cookies in a local user config directory."""

    def __init__(self, settings: AppSettings, repository: AppRepository, logger: Any):
        self.settings = settings
        self.repository = repository
        self.logger = logger

    def _read_cookie_records(self) -> list[dict[str, Any]]:
        path = self.settings.session_store_path
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _write_cookie_records(self, cookies: list[dict[str, Any]], *, status: str, message: str) -> SessionInfo:
        path = self.settings.session_store_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cookies, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return self.repository.save_session_state(
            cookies=cookies, status=status, message=message, last_checked_at=utcnow_iso()
        )

    def serialize_cookie_jar(self, jar: requests.cookies.RequestsCookieJar) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for cookie in jar:
            serialized.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "secure": bool(cookie.secure),
                    "expires": cookie.expires,
                }
            )
        return serialized

    def apply_to_session(self, session: requests.Session) -> None:
        for cookie in self._read_cookie_records():
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain") or "dreamhack.io",
                path=cookie.get("path") or "/",
                secure=bool(cookie.get("secure", False)),
                expires=cookie.get("expires"),
            )

    def import_cookie_header(self, cookie_header: str) -> SessionInfo:
        jar = requests.cookies.RequestsCookieJar()
        for part in cookie_header.split(";"):
            if "=" not in part:
                continue
            name, value = part.strip().split("=", 1)
            if not name:
                continue
            jar.set(name, value, domain="dreamhack.io", path="/")
        cookies = self.serialize_cookie_jar(jar)
        return self._write_cookie_records(cookies, status="unknown", message="Cookies imported from header.")

    def import_cookie_file(self, path: Path) -> SessionInfo:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"{path} is empty")

        if content.startswith("[") or content.startswith("{"):
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                if "cookies" in parsed and isinstance(parsed["cookies"], list):
                    cookies = parsed["cookies"]
                else:
                    cookies = [
                        {"name": key, "value": value, "domain": "dreamhack.io", "path": "/"}
                        for key, value in parsed.items()
                    ]
            else:
                cookies = parsed
            return self._write_cookie_records(cookies, status="unknown", message=f"Cookies imported from {path}.")

        if content.startswith("# Netscape HTTP Cookie File") or "\t" in content:
            cookies: list[dict[str, Any]] = []
            for line in content.splitlines():
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 7:
                    continue
                domain, _, path_value, secure, expires, name, value = parts[:7]
                cookies.append(
                    {
                        "name": name,
                        "value": value,
                        "domain": domain.lstrip("."),
                        "path": path_value,
                        "secure": secure.upper() == "TRUE",
                        "expires": int(expires) if str(expires).isdigit() else None,
                    }
                )
            return self._write_cookie_records(cookies, status="unknown", message=f"Cookies imported from {path}.")

        return self.import_cookie_header(content)

    def clear(self) -> SessionInfo:
        try:
            self.settings.session_store_path.unlink(missing_ok=True)
        except OSError:
            pass
        return self.repository.clear_session_state()

    def get_status(self) -> SessionInfo:
        return self.repository.get_session_state()

    def refresh_status(self, client: Any) -> SessionInfo:
        info = client.inspect_session()
        return self.repository.save_session_state(
            cookies=self._read_cookie_records(), status=info.status, message=info.message, last_checked_at=utcnow_iso()
        )

    def interactive_browser_login(self) -> SessionInfo:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed. Install it to use --browser login.") from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(self.settings.base_url, wait_until="load")
            input("Complete the login in the opened browser window, then press Enter here to save cookies...")
            cookies = [cookie for cookie in context.cookies() if "dreamhack.io" in cookie.get("domain", "")]
            browser.close()

        return self._write_cookie_records(
            cookies, status="unknown", message="Cookies imported from an interactive browser session."
        )
