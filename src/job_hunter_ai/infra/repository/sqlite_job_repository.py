"""SQLite implementation of `JobRepository` (docs/DATA_MODEL.md)."""

import json
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from job_hunter_ai.domain.entities.application_result import ApplicationResult
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.time_utils import from_iso_utc, to_iso_utc, utc_now
from job_hunter_ai.infra.repository.migrations_runner import apply_migrations

_JOB_COLUMNS = "id, source, title, company, description, url, apply_email, raw, collected_at"

_UPSERT_JOB = f"""
INSERT INTO jobs ({_JOB_COLUMNS})
VALUES (:id, :source, :title, :company, :description, :url, :apply_email, :raw, :collected_at)
ON CONFLICT (id) DO UPDATE SET
    source = excluded.source,
    title = excluded.title,
    company = excluded.company,
    description = excluded.description,
    url = excluded.url,
    apply_email = excluded.apply_email,
    raw = excluded.raw
"""


class SqliteJobRepository:
    """Persists jobs and application history in a local SQLite file.

    Creates the database (and its parent directory) on first use and applies any
    pending migration, so a fresh clone works with no manual setup step.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        apply_migrations(self._connection)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def save_jobs(self, jobs: list[Job]) -> list[Job]:
        """Upsert every job and return the persisted state (original `collected_at` kept)."""
        if not jobs:
            return []
        with self._connection:
            self._connection.executemany(_UPSERT_JOB, [self._to_row(job) for job in jobs])
        persisted = (self.get_job(job.id) for job in jobs)
        return [job for job in persisted if job is not None]

    def get_job(self, job_id: str) -> Job | None:
        row = self._connection.execute(
            f"SELECT {_JOB_COLUMNS} FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return self._to_job(row) if row is not None else None

    def save_application(self, result: ApplicationResult) -> None:
        applied_at = result.applied_at or utc_now()
        with self._connection:
            self._connection.execute(
                "INSERT INTO applications (job_id, method, status, applier, detail, applied_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    result.job_id,
                    result.method,
                    result.status,
                    result.applier,
                    result.detail,
                    to_iso_utc(applied_at),
                ),
            )

    def _to_row(self, job: Job) -> dict[str, Any]:
        return {
            "id": job.id,
            "source": job.source,
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "url": job.url,
            "apply_email": job.apply_email,
            "raw": json.dumps(job.raw, ensure_ascii=False),
            "collected_at": to_iso_utc(job.collected_at or utc_now()),
        }

    def _to_job(self, row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            source=row["source"],
            title=row["title"],
            company=row["company"],
            description=row["description"],
            url=row["url"],
            apply_email=row["apply_email"],
            raw=json.loads(row["raw"]),
            collected_at=from_iso_utc(row["collected_at"]),
        )
