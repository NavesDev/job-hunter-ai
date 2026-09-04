import pytest

from job_hunter_ai.application.apply_job import ApplyJobUseCase
from job_hunter_ai.domain.entities.application_result import ApplicationStatus
from job_hunter_ai.domain.errors import InvalidInputError, JobNotFoundError, SmtpError
from tests.fakes import (
    FakeApplierRegistry,
    FakeJobApplier,
    FakeJobRepository,
    build_job,
    build_profile,
)


def build_use_case(tmp_path, applier=None, job=None):
    repository = FakeJobRepository()
    stored = job or build_job()
    repository.save_jobs([stored])
    registry = FakeApplierRegistry(applier)
    return ApplyJobUseCase(repository, registry, build_profile(tmp_path)), repository, stored


def test_apply_job_should_return_sent_when_the_applier_succeeds(tmp_path):
    # Arrange
    use_case, _, job = build_use_case(tmp_path, FakeJobApplier())

    # Act
    result = use_case.execute(job.id, "email")

    # Assert
    assert result.status == ApplicationStatus.SENT
    assert result.job_id == job.id


def test_apply_job_should_record_the_attempt_when_it_succeeds(tmp_path):
    # Arrange
    use_case, repository, job = build_use_case(tmp_path, FakeJobApplier())

    # Act
    use_case.execute(job.id, "email")

    # Assert
    assert [entry.status for entry in repository.applications] == [ApplicationStatus.SENT]


def test_apply_job_should_return_skipped_when_no_applier_is_registered(tmp_path):
    # Arrange
    use_case, _, job = build_use_case(tmp_path, applier=None)

    # Act
    result = use_case.execute(job.id, "form")

    # Assert
    assert result.status == ApplicationStatus.SKIPPED
    assert "form" in result.detail


def test_apply_job_should_record_the_skipped_attempt_when_no_applier_is_registered(tmp_path):
    # Arrange
    use_case, repository, job = build_use_case(tmp_path, applier=None)

    # Act
    use_case.execute(job.id, "form")

    # Assert
    assert [entry.status for entry in repository.applications] == [ApplicationStatus.SKIPPED]


def test_apply_job_should_record_a_failed_attempt_before_propagating_the_error(tmp_path):
    # Arrange
    applier = FakeJobApplier(error=SmtpError("connection refused"))
    use_case, repository, job = build_use_case(tmp_path, applier)

    # Act
    with pytest.raises(SmtpError):
        use_case.execute(job.id, "email")

    # Assert
    recorded = repository.applications[0]
    assert recorded.status == ApplicationStatus.FAILED
    assert recorded.detail == "connection refused"


def test_apply_job_should_append_a_row_for_every_attempt_when_applying_twice(tmp_path):
    # Arrange
    use_case, repository, job = build_use_case(tmp_path, FakeJobApplier())

    # Act
    use_case.execute(job.id, "email")
    use_case.execute(job.id, "email")

    # Assert
    assert len(repository.applications) == 2


def test_apply_job_should_forward_the_options_to_the_applier(tmp_path):
    # Arrange
    applier = FakeJobApplier()
    use_case, _, job = build_use_case(tmp_path, applier)

    # Act
    use_case.execute(job.id, "email", email="hr@acme.com", subject="Hello")

    # Assert
    assert applier.calls[0]["email"] == "hr@acme.com"
    assert applier.calls[0]["subject"] == "Hello"


def test_apply_job_should_resolve_the_applier_with_the_job_source(tmp_path):
    # Arrange
    repository = FakeJobRepository()
    job = build_job(source="manual")
    repository.save_jobs([job])
    registry = FakeApplierRegistry(FakeJobApplier())
    use_case = ApplyJobUseCase(repository, registry, build_profile(tmp_path))

    # Act
    use_case.execute(job.id, "email")

    # Assert
    assert registry.calls == [("email", "manual")]


def test_apply_job_should_raise_job_not_found_when_the_id_is_unknown(tmp_path):
    # Arrange
    use_case, _, _ = build_use_case(tmp_path, FakeJobApplier())

    # Act / Assert
    with pytest.raises(JobNotFoundError) as error:
        use_case.execute("manual:deadbeefcafe", "email")
    assert error.value.code == "JOB_NOT_FOUND"


def test_apply_job_should_raise_invalid_input_when_the_job_id_is_empty(tmp_path):
    # Arrange
    use_case, _, _ = build_use_case(tmp_path, FakeJobApplier())

    # Act / Assert
    with pytest.raises(InvalidInputError):
        use_case.execute("", "email")
