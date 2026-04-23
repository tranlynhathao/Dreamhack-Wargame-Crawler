"""FastAPI application for the local-only backend."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from dreamhack_local.app import AppContext, build_app_context
from dreamhack_local.models.schemas import (
    BulkDownloadRequest,
    ChallengeDetailResponse,
    ChallengeRecord,
    CrawlChallengeRequest,
    CrawlSyncRequest,
    DoctorReport,
    JobRecord,
    OpenFolderRequest,
    OpenFolderResponse,
    SessionImportRequest,
    SessionInfo,
    SettingsUpdateRequest,
    SettingsView,
    StatsResponse,
)


def create_api_app() -> FastAPI:
    context = build_app_context()
    app = FastAPI(title="DreamHack Local", version="0.1.0")
    app.state.context = context

    if context.settings.enable_localhost_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[],
            allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def ctx() -> AppContext:
        return app.state.context

    def fresh_context() -> AppContext:
        return build_app_context()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/session", response_model=SessionInfo)
    def session_status(refresh: bool = True) -> SessionInfo:
        if refresh:
            return ctx().session_service.refresh_status(ctx().client)
        return ctx().session_service.get_status()

    @app.post("/api/session/import", response_model=SessionInfo)
    def session_import(request: SessionImportRequest) -> SessionInfo:
        if request.cookie_header:
            result = ctx().session_service.import_cookie_header(request.cookie_header)
        elif request.cookie_file:
            result = ctx().session_service.import_cookie_file(Path(request.cookie_file).expanduser())
        else:
            raise HTTPException(status_code=400, detail="Provide cookie_header or cookie_file.")
        ctx().client.refresh_session()
        return result

    @app.post("/api/session/clear", response_model=SessionInfo)
    def session_clear() -> SessionInfo:
        result = ctx().session_service.clear()
        ctx().client.refresh_session()
        return result

    @app.post("/api/session/test", response_model=SessionInfo)
    def session_test() -> SessionInfo:
        return ctx().session_service.refresh_status(ctx().client)

    @app.post("/api/crawl/sync", response_model=JobRecord)
    def crawl_sync(request: CrawlSyncRequest) -> JobRecord:
        return ctx().job_service.enqueue(
            kind="crawl.sync",
            payload=request.model_dump(),
            runner=lambda progress: fresh_context().crawl_service.sync(
                category=request.category,
                difficulty=request.difficulty,
                status=request.status,
                max_pages=request.max_pages,
                progress_cb=progress,
            ),
        )

    @app.post("/api/crawl/challenge", response_model=JobRecord)
    def crawl_challenge(request: CrawlChallengeRequest) -> JobRecord:
        return ctx().job_service.enqueue(
            kind="crawl.challenge",
            payload=request.model_dump(),
            runner=lambda progress: fresh_context().crawl_service.crawl_challenge(
                request.identifier, progress_cb=progress
            ),
        )

    @app.get("/api/challenges", response_model=list[ChallengeRecord])
    def list_challenges(
        category: str | None = None,
        difficulty: int | None = None,
        status: str | None = None,
        author: str | None = None,
        downloaded: bool | None = None,
        search: str | None = None,
        limit: Annotated[int, Query(ge=1, le=10_000)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[ChallengeRecord]:
        return ctx().challenge_service.list_challenges(
            category=category,
            difficulty=difficulty,
            status=status,
            author=author,
            downloaded=downloaded,
            search=search,
            limit=limit,
            offset=offset,
        )

    @app.get("/api/challenges/{challenge_id}", response_model=ChallengeDetailResponse)
    def get_challenge(challenge_id: str) -> ChallengeDetailResponse:
        challenge = ctx().challenge_service.get_challenge(challenge_id)
        if challenge is None:
            raise HTTPException(status_code=404, detail=f"Challenge {challenge_id} was not found.")
        return ChallengeDetailResponse(
            challenge=challenge, files=ctx().repository.list_challenge_files(challenge.challenge_id)
        )

    @app.get("/api/stats", response_model=StatsResponse)
    def stats() -> StatsResponse:
        return ctx().repository.get_stats()

    @app.post("/api/challenges/{challenge_id}/download", response_model=JobRecord)
    def download_challenge(challenge_id: str, mode: str = "resume") -> JobRecord:
        return ctx().job_service.enqueue(
            kind="download.challenge",
            payload={"challenge_id": challenge_id, "mode": mode},
            runner=lambda progress: fresh_context().download_service.download_challenge(
                challenge_id, mode=mode, progress_cb=progress
            ),
        )

    @app.post("/api/downloads/bulk", response_model=JobRecord)
    def downloads_bulk(request: BulkDownloadRequest) -> JobRecord:
        return ctx().job_service.enqueue(
            kind="download.bulk",
            payload=request.model_dump(),
            runner=lambda progress: fresh_context().download_service.bulk_download(
                category=request.category,
                difficulty=request.difficulty,
                status=request.status,
                downloaded=request.downloaded,
                search=request.search,
                mode=request.mode,
                progress_cb=progress,
            ),
        )

    @app.get("/api/jobs", response_model=list[JobRecord])
    def jobs() -> list[JobRecord]:
        return ctx().repository.list_jobs()

    @app.get("/api/jobs/{job_id}", response_model=JobRecord)
    def job(job_id: str) -> JobRecord:
        result = ctx().repository.get_job(job_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.")
        return result

    @app.get("/api/settings", response_model=SettingsView)
    def settings() -> SettingsView:
        return ctx().challenge_service.get_settings_view()

    @app.put("/api/settings", response_model=SettingsView)
    def settings_update(request: SettingsUpdateRequest) -> SettingsView:
        updated = ctx().challenge_service.update_settings(**request.model_dump())
        app.state.context = build_app_context()
        return updated

    @app.post("/api/export/manifest")
    def export_manifest(sort_by: str = "id", sort_order: str = "desc") -> dict[str, str]:
        path = ctx().challenge_service.export_manifest(sort_by=sort_by, sort_order=sort_order)
        return {"path": str(path)}

    @app.post("/api/sync/files")
    def sync_files() -> dict[str, int]:
        return ctx().challenge_service.sync_files()

    @app.post("/api/doctor", response_model=DoctorReport)
    def doctor() -> DoctorReport:
        return ctx().challenge_service.doctor()

    @app.post("/api/open-folder", response_model=OpenFolderResponse)
    def open_folder(request: OpenFolderRequest) -> OpenFolderResponse:
        try:
            path = ctx().challenge_service.open_folder(challenge_id=request.challenge_id, path=request.path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return OpenFolderResponse(path=str(path))

    return app
