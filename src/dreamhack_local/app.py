"""Application container used by the CLI and API layers."""

from __future__ import annotations

from dataclasses import dataclass

from dreamhack_local.config import AppSettings, load_settings
from dreamhack_local.core.logging import setup_logging
from dreamhack_local.crawler.client import DreamhackClient
from dreamhack_local.services.challenge_service import ChallengeService
from dreamhack_local.services.crawl_service import CrawlService
from dreamhack_local.services.download_service import DownloadService
from dreamhack_local.services.job_service import JobService
from dreamhack_local.services.manifest_service import ManifestService
from dreamhack_local.services.session_service import SessionService
from dreamhack_local.services.workspace_service import WorkspaceService
from dreamhack_local.storage.database import Database
from dreamhack_local.storage.repository import AppRepository


@dataclass
class AppContext:
    settings: AppSettings
    repository: AppRepository
    session_service: SessionService
    client: DreamhackClient
    workspace_service: WorkspaceService
    manifest_service: ManifestService
    challenge_service: ChallengeService
    crawl_service: CrawlService
    download_service: DownloadService
    job_service: JobService


def build_app_context(settings: AppSettings | None = None) -> AppContext:
    settings = settings or load_settings()
    logger = setup_logging(settings.log_level)
    database = Database(settings.database_path)
    database.initialize()
    repository = AppRepository(database)
    session_service = SessionService(settings, repository, logger)
    client = DreamhackClient(settings, session_service, logger)
    workspace_service = WorkspaceService(settings, repository, logger)
    manifest_service = ManifestService(settings, repository, logger)
    challenge_service = ChallengeService(
        settings, repository, workspace_service, manifest_service, session_service, logger
    )
    crawl_service = CrawlService(settings, repository, client, workspace_service, logger)
    download_service = DownloadService(settings, repository, client, workspace_service, logger)
    job_service = JobService(repository, logger)

    repository.set_app_setting("workspace_root", str(settings.workspace_root))
    repository.set_app_setting("database_path", str(settings.database_path))

    if repository.challenge_count() == 0:
        imported = challenge_service.bootstrap_from_manifest()
        if imported:
            workspace_service.sync_from_disk()
            logger.info("Bootstrapped %s challenges from legacy manifest.json", imported)

    return AppContext(
        settings=settings,
        repository=repository,
        session_service=session_service,
        client=client,
        workspace_service=workspace_service,
        manifest_service=manifest_service,
        challenge_service=challenge_service,
        crawl_service=crawl_service,
        download_service=download_service,
        job_service=job_service,
    )
