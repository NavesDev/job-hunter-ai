import sqlite3
from dataclasses import replace
from datetime import UTC, datetime

from job_hunter_ai.domain.entities.application_result import ApplicationResult, ApplicationStatus
from job_hunter_ai.infra.repository.sqlite_job_repository import SqliteJobRepository
from tests.fakes import build_job


def open_repository(tmp_path, name="jobs.db"):
    return SqliteJobRepository(tmp_path / "local" / name)


def test_repository_should_create_the_database_and_schema_when_it_does_not_exist(tmp_path):
    # Arrange
    database_path = tmp_path / "local" / "jobs.db"

    # Act
    with SqliteJobRepository(database_path):
        pass

    # Assert
    with sqlite3.connect(database_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert {"jobs", "applications", "schema_version"} <= tables


def test_repository_should_round_trip_every_job_field_when_saving_and_reading_back(tmp_path):
    # Arrange
    job = build_job(raw={"extra": "payload"})

    # Act
    with open_repository(tmp_path) as repository:
        repository.save_jobs([job])
        stored = repository.get_job(job.id)

    # Assert
    assert stored is not None
    assert (stored.title, stored.company, stored.url) == (job.title, job.company, job.url)
    assert stored.apply_email == job.apply_email
    assert stored.raw == {"extra": "payload"}


def test_repository_should_not_duplicate_a_row_when_the_same_job_is_saved_twice(tmp_path):
    # Arrange
    job = build_job()

    # Act
    with open_repository(tmp_path) as repository:
        repository.save_jobs([job])
        repository.save_jobs([job])
        count = repository._connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    # Assert
    assert count == 1


def test_repository_should_preserve_the_first_collected_at_when_the_job_is_saved_again(tmp_path):
    # Arrange
    first = build_job(collected_at=datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC))
    later = replace(first, collected_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC))

    # Act
    with open_repository(tmp_path) as repository:
        repository.save_jobs([first])
        persisted = repository.save_jobs([later])

    # Assert
    assert persisted[0].collected_at == first.collected_at


def test_repository_should_refresh_the_mutable_fields_when_the_job_is_saved_again(tmp_path):
    # Arrange
    original = build_job(description="Python, SQL")
    updated = replace(original, description="Python, SQL, Kubernetes")

    # Act
    with open_repository(tmp_path) as repository:
        repository.save_jobs([original])
        persisted = repository.save_jobs([updated])

    # Assert
    assert persisted[0].description == "Python, SQL, Kubernetes"


def test_repository_should_return_none_when_the_job_id_is_unknown(tmp_path):
    # Arrange / Act
    with open_repository(tmp_path) as repository:
        stored = repository.get_job("manual:deadbeefcafe")

    # Assert
    assert stored is None


def test_repository_should_return_an_empty_list_when_there_is_nothing_to_save(tmp_path):
    # Arrange / Act
    with open_repository(tmp_path) as repository:
        persisted = repository.save_jobs([])

    # Assert
    assert persisted == []


def test_repository_should_append_a_row_for_every_application_attempt(tmp_path):
    # Arrange
    job = build_job()
    result = ApplicationResult(
        job_id=job.id, method="email", status=ApplicationStatus.SENT, applier="email"
    )

    # Act
    with open_repository(tmp_path) as repository:
        repository.save_jobs([job])
        repository.save_application(result)
        repository.save_application(result)
        count = repository._connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0]

    # Assert
    assert count == 2


def test_repository_should_apply_each_migration_only_once_when_reopened(tmp_path):
    # Arrange
    with open_repository(tmp_path):
        pass

    # Act
    with open_repository(tmp_path) as repository:
        rows = repository._connection.execute("SELECT version FROM schema_version").fetchall()

    # Assert
    assert [row[0] for row in rows] == [1]
