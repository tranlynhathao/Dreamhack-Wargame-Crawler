"""Background job execution for the localhost API."""

from __future__ import annotations

import threading
from typing import Any, Callable

from dreamhack_local.storage.repository import AppRepository, utcnow_iso

JobRunner = Callable[[Callable[[float, str, dict[str, Any] | None], None]], dict[str, Any]]


class JobService:
    """Simple threaded job runner backed by the jobs table."""

    def __init__(self, repository: AppRepository, logger: Any):
        self.repository = repository
        self.logger = logger

    def enqueue(self, *, kind: str, payload: dict[str, Any] | None, runner: JobRunner):
        job = self.repository.create_job(kind=kind, payload=payload or {})

        def progress(progress_value: float, message: str, result: dict[str, Any] | None = None) -> None:
            self.repository.update_job(
                job.job_id,
                status="running",
                progress=max(0.0, min(progress_value, 1.0)),
                message=message,
                result=result or {},
                started_at=utcnow_iso(),
            )

        def wrapped() -> None:
            try:
                self.repository.update_job(job.job_id, status="running", started_at=utcnow_iso(), message="Job started")
                result = runner(progress)
                self.repository.update_job(
                    job.job_id,
                    status="completed",
                    progress=1.0,
                    message="Job completed",
                    result=result,
                    finished_at=utcnow_iso(),
                )
            except Exception as exc:
                self.repository.update_job(
                    job.job_id, status="failed", message=str(exc), error=str(exc), finished_at=utcnow_iso()
                )

        thread = threading.Thread(target=wrapped, daemon=True)
        thread.start()
        return job
