from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from dreamhack_local.api.app import create_api_app
from dreamhack_local.app import AppContext
from dreamhack_local.cli.app import app as cli_app
from dreamhack_local.config import AppSettings
from dreamhack_local.core.exceptions import AccessDeniedError
from dreamhack_local.models.schemas import SessionInfo
from dreamhack_local.services.challenge_service import ChallengeService
from dreamhack_local.services.download_service import DownloadService
from dreamhack_local.services.job_service import JobService
from dreamhack_local.services.manifest_service import ManifestService
from dreamhack_local.services.session_service import SessionService
from dreamhack_local.services.workspace_service import WorkspaceService
from dreamhack_local.storage.database import Database
from dreamhack_local.storage.repository import AppRepository


class FakeResponse:
    def __init__(
        self,
        *,
        url: str,
        headers: dict[str, str] | None = None,
        chunks: list[bytes] | None = None,
        status_code: int = 200,
    ) -> None:
        self.url = url
        self.headers = headers or {}
        self.status_code = status_code
        self._chunks = chunks or []

    def iter_content(self, chunk_size: int = 1024 * 256):
        yield from self._chunks

    def close(self) -> None:
        return None


class FakeClient:
    def __init__(self, detail_html: str, responses: dict[str, FakeResponse]) -> None:
        self.detail_html = detail_html
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def fetch_challenge_html(self, challenge_id: int) -> str:
        self.calls.append(("FETCH_DETAIL", str(challenge_id), {}))
        return self.detail_html

    def request(self, method: str, url: str, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses[url]

    def validate_download_response(self, response, *, source_url: str, first_chunk: bytes) -> None:
        content_type = response.headers.get("Content-Type", "").lower()
        preview = first_chunk.decode("utf-8", errors="ignore").lower()
        if content_type.startswith("text/html") and ("login" in preview or "dreamhack" in preview):
            raise AccessDeniedError(f"Download {source_url} returned an HTML page instead of a file.")


def make_context(tmp_path: Path, *, response: FakeResponse) -> AppContext:
    settings = AppSettings(
        repo_root=tmp_path,
        workspace_root=tmp_path / "workspace",
        database_path=tmp_path / "data" / "dreamhack.db",
        manifest_export_path=tmp_path / "manifest.json",
        config_dir=tmp_path / "config",
        settings_store_path=tmp_path / "config" / "settings.json",
        session_store_path=tmp_path / "config" / "session.json",
    )
    logger = logging.getLogger(f"download-test-{tmp_path.name}")
    database = Database(settings.database_path)
    database.initialize()
    repository = AppRepository(database)
    session_service = SessionService(settings, repository, logger)
    fake_client = FakeClient(
        Path("tests/fixtures/detail_sample.html").read_text(encoding="utf-8"),
        {"https://files.example.com/attachment.zip?token=abc": response},
    )
    workspace_service = WorkspaceService(settings, repository, logger)
    manifest_service = ManifestService(settings, repository, logger)
    challenge_service = ChallengeService(
        settings, repository, workspace_service, manifest_service, session_service, logger
    )
    download_service = DownloadService(settings, repository, fake_client, workspace_service, logger)
    job_service = JobService(repository, logger)

    repository.upsert_challenge(
        {
            "challenge_id": 123,
            "title": "Neat Web Challenge",
            "slug": "neat-web-challenge",
            "url": "https://dreamhack.io/wargame/challenges/123",
            "category": "web",
            "category_display": "Web",
            "difficulty": 4,
            "difficulty_label": "4",
        }
    )

    return AppContext(
        settings=settings,
        repository=repository,
        session_service=session_service,
        client=fake_client,  # type: ignore[arg-type]
        workspace_service=workspace_service,
        manifest_service=manifest_service,
        challenge_service=challenge_service,
        crawl_service=None,  # type: ignore[arg-type]
        download_service=download_service,
        job_service=job_service,
    )


def wait_for_job(client: TestClient, job_id: str, *, timeout: float = 3.0) -> dict[str, object]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = client.get(f"/api/jobs/{job_id}").json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} did not finish within {timeout} seconds")


def test_download_service_saves_metadata_description_and_files(tmp_path: Path) -> None:
    context = make_context(
        tmp_path,
        response=FakeResponse(
            url="https://files.example.com/attachment.zip?token=abc",
            headers={"Content-Disposition": 'attachment; filename="challenge.zip"', "Content-Type": "application/zip"},
            chunks=[b"PK\x03\x04example-zip-bytes"],
        ),
    )

    result = context.download_service.download_challenge("123")

    folder = Path(result["local_path"])
    assert folder.exists()
    assert (folder / "metadata.json").exists()
    assert (folder / "description.md").read_text(encoding="utf-8").strip()
    assert (folder / "files" / "challenge.zip").read_bytes() == b"PK\x03\x04example-zip-bytes"

    refreshed = context.repository.get_challenge(123)
    assert refreshed is not None
    assert refreshed.download_status == "files_downloaded"
    assert refreshed.downloaded is True
    assert refreshed.file_count == 1
    assert refreshed.byte_count == len(b"PK\x03\x04example-zip-bytes")
    assert refreshed.last_error is None
    assert any(call[0] == "GET" for call in context.client.calls)


def test_download_service_rejects_html_login_page_and_persists_failure(tmp_path: Path) -> None:
    context = make_context(
        tmp_path,
        response=FakeResponse(
            url="https://dreamhack.io/login",
            headers={"Content-Type": "text/html"},
            chunks=[b"<html><title>DreamHack Login</title>login</html>"],
        ),
    )

    try:
        context.download_service.download_challenge("123")
    except AccessDeniedError:
        pass
    else:
        raise AssertionError("Expected AccessDeniedError")

    refreshed = context.repository.get_challenge(123)
    assert refreshed is not None
    assert refreshed.download_status == "failed"
    assert refreshed.file_count == 0
    assert "html page instead of a file" in (refreshed.last_error or "").lower()
    assert Path(refreshed.local_path).exists()
    assert (Path(refreshed.local_path) / "metadata.json").exists()


def test_api_download_route_runs_real_job(tmp_path: Path, monkeypatch) -> None:
    context = make_context(
        tmp_path,
        response=FakeResponse(
            url="https://files.example.com/attachment.zip?token=abc",
            headers={"Content-Disposition": 'attachment; filename="challenge.zip"', "Content-Type": "application/zip"},
            chunks=[b"api-job-bytes"],
        ),
    )
    monkeypatch.setattr("dreamhack_local.api.app.build_app_context", lambda: context)

    client = TestClient(create_api_app())
    queued = client.post("/api/challenges/123/download")
    assert queued.status_code == 200
    job_id = queued.json()["job_id"]

    finished = wait_for_job(client, job_id)
    assert finished["status"] == "completed"
    assert finished["result"]["download_status"] == "files_downloaded"
    assert Path(finished["result"]["local_path"]).exists()
    assert (Path(finished["result"]["local_path"]) / "files" / "challenge.zip").read_bytes() == b"api-job-bytes"


def test_cli_download_uses_same_service(tmp_path: Path, monkeypatch) -> None:
    context = make_context(
        tmp_path,
        response=FakeResponse(
            url="https://files.example.com/attachment.zip?token=abc",
            headers={"Content-Disposition": 'attachment; filename="challenge.zip"', "Content-Type": "application/zip"},
            chunks=[b"cli-zip-bytes"],
        ),
    )
    monkeypatch.setattr("dreamhack_local.app.build_app_context", lambda: context)

    runner = CliRunner()
    result = runner.invoke(cli_app, ["download", "123", "--json"])
    assert result.exit_code == 0
    assert "files_downloaded" in result.stdout
    assert (
        context.settings.workspace_root / "Web" / "Level_4" / "Neat_Web_Challenge" / "files" / "challenge.zip"
    ).read_bytes() == b"cli-zip-bytes"
