"""Download challenge attachments and persist local metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from dreamhack_local.config import AppSettings
from dreamhack_local.crawler.client import DreamhackClient
from dreamhack_local.crawler.parser import ParsedChallengeDetail, ParsedDownload, parse_detail
from dreamhack_local.models.schemas import ChallengeFileRecord, ChallengeRecord
from dreamhack_local.storage.repository import AppRepository, utcnow_iso
from dreamhack_local.utils.files import infer_filename, sanitize_filename, sha256_file

ProgressCallback = Callable[[float, str, dict[str, Any] | None], None]
DownloadMode = Literal["skip", "overwrite", "resume"]


class DownloadService:
    """Downloads challenge files with the authenticated local session."""

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

    def _detail_url(self, challenge_id: int) -> str:
        return f"{self.settings.base_url}/wargame/challenges/{challenge_id}"

    def _metadata_for_downloads(self, detail: ParsedChallengeDetail) -> dict[str, Any]:
        return {
            "download_urls": [download.url for download in detail.downloads],
            "download_labels": [download.label for download in detail.downloads if download.label],
        }

    def _status_for_local_metadata(self, challenge: ChallengeRecord) -> str:
        if challenge.description_text or challenge.description_html:
            return "description_saved"
        return "metadata_only"

    def _persist_challenge(
        self,
        challenge: ChallengeRecord,
        *,
        detail: ParsedChallengeDetail | None = None,
        local_path: Path | None = None,
        downloaded: bool | None = None,
        last_error: str | None = None,
        last_downloaded_at: str | None = None,
        parse_warnings: list[str] | None = None,
    ) -> ChallengeRecord:
        payload: dict[str, Any] = {
            "challenge_id": challenge.challenge_id,
            "local_path": str(local_path) if local_path else challenge.local_path,
            "downloaded": challenge.downloaded if downloaded is None else downloaded,
            "last_error": last_error,
            "last_downloaded_at": last_downloaded_at,
        }
        if detail is not None:
            payload.update(
                {
                    "title": detail.title or challenge.title,
                    "description_text": detail.description_text or challenge.description_text,
                    "description_html": detail.description_html or challenge.description_html,
                    "has_attachments": bool(detail.downloads),
                    "metadata": self._metadata_for_downloads(detail),
                }
            )
        if parse_warnings is not None:
            payload["parse_warnings"] = parse_warnings
        return self.repository.upsert_challenge(payload)

    def _failure_file_record(
        self, challenge_id: int, download: ParsedDownload, message: str, folder: Path, filename: str | None = None
    ) -> ChallengeFileRecord:
        fallback = filename or sanitize_filename(download.label, fallback=f"challenge-{challenge_id}.bin")
        return ChallengeFileRecord(
            challenge_id=challenge_id,
            filename=fallback,
            relative_path=str((Path("files") / fallback)),
            source_url=download.url,
            status="failed",
            last_error=message,
            downloaded_at=datetime.now(timezone.utc),
        )

    def _existing_download_record(
        self, challenge_id: int, folder: Path, target_path: Path, download: ParsedDownload
    ) -> ChallengeFileRecord:
        return ChallengeFileRecord(
            challenge_id=challenge_id,
            filename=target_path.name,
            relative_path=str(target_path.relative_to(folder)),
            source_url=download.url,
            size_bytes=target_path.stat().st_size,
            checksum_sha256=sha256_file(target_path),
            downloaded_at=datetime.fromtimestamp(target_path.stat().st_mtime, tz=timezone.utc),
        )

    def _download_single_file(
        self,
        challenge: ChallengeRecord,
        *,
        folder: Path,
        files_dir: Path,
        download: ParsedDownload,
        mode: DownloadMode,
        existing_by_url: dict[str, ChallengeFileRecord],
    ) -> tuple[ChallengeFileRecord, str]:
        existing = existing_by_url.get(download.url)
        if existing and mode in {"skip", "resume"}:
            target_path = folder / existing.relative_path
            if target_path.exists():
                self.logger.info("Reusing existing file for challenge %s: %s", challenge.challenge_id, target_path)
                return self._existing_download_record(challenge.challenge_id, folder, target_path, download), "skipped"

        response = self.client.request("GET", download.url, stream=True)
        filename = infer_filename(
            response,
            download.url,
            fallback=sanitize_filename(download.label, fallback=f"challenge-{challenge.challenge_id}.bin"),
        )
        target_path = files_dir / filename

        if target_path.exists():
            if mode in {"skip", "resume"}:
                self.logger.info("Skipping existing target for challenge %s: %s", challenge.challenge_id, target_path)
                response.close()
                return self._existing_download_record(challenge.challenge_id, folder, target_path, download), "skipped"
            if mode == "overwrite":
                target_path.unlink()

        iterator = response.iter_content(chunk_size=1024 * 256)
        try:
            first_chunk = next(iterator, b"")
            self.client.validate_download_response(response, source_url=download.url, first_chunk=first_chunk)

            with target_path.open("wb") as handle:
                if first_chunk:
                    handle.write(first_chunk)
                for chunk in iterator:
                    if chunk:
                        handle.write(chunk)
        except Exception:
            response.close()
            try:
                target_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        response.close()

        self.logger.info("Downloaded challenge %s attachment to %s", challenge.challenge_id, target_path)
        return (
            ChallengeFileRecord(
                challenge_id=challenge.challenge_id,
                filename=filename,
                relative_path=str(target_path.relative_to(folder)),
                source_url=download.url,
                content_type=response.headers.get("Content-Type"),
                size_bytes=target_path.stat().st_size,
                checksum_sha256=sha256_file(target_path),
                downloaded_at=datetime.now(timezone.utc),
            ),
            "downloaded",
        )

    def download_challenge(
        self, identifier: str, *, mode: DownloadMode = "resume", progress_cb: ProgressCallback | None = None
    ) -> dict[str, Any]:
        challenge = self.repository.resolve_challenge(identifier)
        if challenge is None:
            raise ValueError(f"Unknown challenge identifier: {identifier}")

        folder = self.workspace_service.ensure_challenge_folder(challenge)
        files_dir = folder / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        existing_records = self.repository.list_challenge_files(challenge.challenge_id)
        existing_by_url = {
            record.source_url: record
            for record in existing_records
            if record.source_url and record.status == "downloaded"
        }

        detail: ParsedChallengeDetail | None = None
        try:
            self.logger.info("Starting download for challenge %s into %s", challenge.challenge_id, folder)
            detail_html = self.client.fetch_challenge_html(challenge.challenge_id)
            detail = parse_detail(
                detail_html,
                challenge_id=challenge.challenge_id,
                url=challenge.url or self._detail_url(challenge.challenge_id),
            )
            warnings = sorted(set(challenge.parse_warnings + detail.warnings))
            challenge = self._persist_challenge(
                challenge, detail=detail, local_path=folder, downloaded=False, last_error=None, parse_warnings=warnings
            )
            challenge = self.repository.get_challenge(challenge.challenge_id) or challenge
            self.workspace_service.persist_challenge_artifacts(challenge, files=existing_records)

            if not detail.downloads:
                challenge = self._persist_challenge(
                    challenge,
                    detail=detail,
                    local_path=folder,
                    downloaded=False,
                    last_error=None,
                    last_downloaded_at=utcnow_iso(),
                    parse_warnings=sorted(set(challenge.parse_warnings + detail.warnings)),
                )
                challenge = self.repository.get_challenge(challenge.challenge_id) or challenge
                self.workspace_service.persist_challenge_artifacts(challenge, files=existing_records)
                status = challenge.download_status
                self.logger.info(
                    "Challenge %s has no downloadable attachments; saved local metadata only", challenge.challenge_id
                )
                if progress_cb:
                    progress_cb(
                        1.0,
                        f"No downloadable attachments for challenge {challenge.challenge_id}.",
                        {
                            "challenge_id": challenge.challenge_id,
                            "download_status": status,
                            "downloaded_files": 0,
                            "failed_files": 0,
                            "skipped_files": 0,
                            "byte_count": 0,
                            "local_path": str(folder),
                        },
                    )
                return {
                    "challenge_id": challenge.challenge_id,
                    "download_status": status,
                    "downloaded_files": 0,
                    "failed_files": 0,
                    "skipped_files": 0,
                    "byte_count": 0,
                    "local_path": str(folder),
                    "message": "No downloadable attachments were available; metadata and description were saved locally.",
                }

            file_records: list[ChallengeFileRecord] = []
            downloaded_count = 0
            failed_count = 0
            skipped_count = 0
            total_bytes = 0
            errors: list[str] = []
            failure_exceptions: list[Exception] = []

            for index, download in enumerate(detail.downloads, start=1):
                try:
                    record, outcome = self._download_single_file(
                        challenge,
                        folder=folder,
                        files_dir=files_dir,
                        download=download,
                        mode=mode,
                        existing_by_url=existing_by_url,
                    )
                    file_records.append(record)
                    if outcome == "downloaded":
                        downloaded_count += 1
                    else:
                        skipped_count += 1
                    total_bytes += record.size_bytes or 0
                    if progress_cb:
                        progress_cb(
                            index / len(detail.downloads),
                            f"{outcome.title()} {record.filename}",
                            {
                                "challenge_id": challenge.challenge_id,
                                "filename": record.filename,
                                "downloaded_files": downloaded_count,
                                "failed_files": failed_count,
                                "skipped_files": skipped_count,
                                "byte_count": total_bytes,
                            },
                        )
                except Exception as exc:
                    failed_count += 1
                    message = str(exc)
                    errors.append(message)
                    failure_exceptions.append(exc)
                    failed_record = self._failure_file_record(challenge.challenge_id, download, message, folder)
                    file_records.append(failed_record)
                    self.logger.warning(
                        "Challenge %s attachment download failed for %s: %s",
                        challenge.challenge_id,
                        download.url,
                        message,
                    )
                    if progress_cb:
                        progress_cb(
                            index / len(detail.downloads),
                            f"Failed {failed_record.filename}",
                            {
                                "challenge_id": challenge.challenge_id,
                                "filename": failed_record.filename,
                                "downloaded_files": downloaded_count,
                                "failed_files": failed_count,
                                "skipped_files": skipped_count,
                                "byte_count": total_bytes,
                                "last_error": message,
                            },
                        )

            self.repository.replace_challenge_files(challenge.challenge_id, file_records)
            last_error = "; ".join(errors[:3]) if errors else None
            downloaded_flag = downloaded_count > 0 or any(record.status == "downloaded" for record in file_records)
            challenge = self._persist_challenge(
                challenge,
                detail=detail,
                local_path=folder,
                downloaded=downloaded_flag,
                last_error=last_error,
                last_downloaded_at=utcnow_iso(),
                parse_warnings=sorted(set(challenge.parse_warnings + detail.warnings)),
            )
            challenge = self.repository.get_challenge(challenge.challenge_id) or challenge
            self.workspace_service.persist_challenge_artifacts(challenge, files=file_records)

            result = {
                "challenge_id": challenge.challenge_id,
                "download_status": challenge.download_status,
                "downloaded_files": downloaded_count,
                "failed_files": failed_count,
                "skipped_files": skipped_count,
                "byte_count": total_bytes,
                "local_path": str(folder),
            }
            if failed_count and not downloaded_flag:
                if failure_exceptions:
                    raise failure_exceptions[0]
                raise RuntimeError(last_error or f"All downloads failed for challenge {challenge.challenge_id}.")
            if progress_cb:
                progress_cb(1.0, f"Download finished for challenge {challenge.challenge_id}", result)
            return result
        except Exception as exc:
            self.logger.exception("Download failed for challenge %s: %s", challenge.challenge_id, exc)
            challenge = self._persist_challenge(
                challenge,
                detail=detail,
                local_path=folder,
                downloaded=False,
                last_error=str(exc),
                last_downloaded_at=utcnow_iso(),
                parse_warnings=sorted(set(challenge.parse_warnings + (detail.warnings if detail else []))),
            )
            self.workspace_service.persist_challenge_artifacts(
                challenge, files=self.repository.list_challenge_files(challenge.challenge_id)
            )
            raise

    def bulk_download(
        self,
        *,
        category: str | None = None,
        difficulty: int | None = None,
        status: str | None = None,
        downloaded: bool | None = None,
        search: str | None = None,
        mode: DownloadMode = "resume",
        progress_cb: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        challenges = self.repository.list_challenges(
            category=category,
            difficulty=difficulty,
            status=status,
            downloaded=downloaded,
            search=search,
            limit=1_000_000,
        )
        total = len(challenges)
        completed = 0
        succeeded = 0
        failed = 0
        skipped = 0
        results: list[dict[str, Any]] = []

        for challenge in challenges:
            try:
                result = self.download_challenge(str(challenge.challenge_id), mode=mode)
                results.append(result)
                completed += 1
                succeeded += 1
                skipped += int(result.get("skipped_files", 0))
            except Exception as exc:
                completed += 1
                failed += 1
                message = str(exc)
                self.logger.warning("Bulk download failed for challenge %s: %s", challenge.challenge_id, message)
                results.append({"challenge_id": challenge.challenge_id, "download_status": "failed", "error": message})
            if progress_cb:
                progress_cb(
                    completed / max(total, 1),
                    f"Processed {completed}/{total} downloads",
                    {
                        "challenge_id": challenge.challenge_id,
                        "succeeded": succeeded,
                        "failed": failed,
                        "skipped": skipped,
                    },
                )

        return {"count": completed, "succeeded": succeeded, "failed": failed, "skipped": skipped, "results": results}
