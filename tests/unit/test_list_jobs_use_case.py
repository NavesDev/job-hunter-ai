import pytest

from job_hunter_ai.application.list_jobs import DEFAULT_MAX_LENGTH, ListJobsUseCase
from job_hunter_ai.domain.errors import InvalidInputError
from tests.fakes import FakeJobRepository, FakeJobSource, build_job


def test_list_jobs_should_return_the_persisted_jobs_when_the_source_yields_them():
    # Arrange
    source = FakeJobSource([build_job(title="Backend Engineer")])
    repository = FakeJobRepository()
    use_case = ListJobsUseCase(source, repository)

    # Act
    jobs = use_case.execute()

    # Assert
    assert [job.title for job in jobs] == ["Backend Engineer"]
    assert list(repository.jobs) == [jobs[0].id]


def test_list_jobs_should_cap_the_result_when_max_length_is_smaller_than_the_source():
    # Arrange
    source = FakeJobSource([build_job(title=f"Role {index}") for index in range(5)])
    use_case = ListJobsUseCase(source, FakeJobRepository())

    # Act
    jobs = use_case.execute(max_length=2)

    # Assert
    assert len(jobs) == 2


def test_list_jobs_should_default_max_length_to_50_when_the_flag_is_omitted():
    # Arrange
    source = FakeJobSource()
    use_case = ListJobsUseCase(source, FakeJobRepository())

    # Act
    use_case.execute()

    # Assert
    assert source.calls[0]["max_length"] == DEFAULT_MAX_LENGTH


def test_list_jobs_should_forward_source_options_when_extra_arguments_are_given():
    # Arrange
    source = FakeJobSource()
    use_case = ListJobsUseCase(source, FakeJobRepository())

    # Act
    use_case.execute(file="jobs.json")

    # Assert
    assert source.calls[0]["file"] == "jobs.json"


def test_list_jobs_should_raise_invalid_input_when_max_length_is_not_positive():
    # Arrange
    use_case = ListJobsUseCase(FakeJobSource(), FakeJobRepository())

    # Act / Assert
    with pytest.raises(InvalidInputError):
        use_case.execute(max_length=0)


def test_list_jobs_should_keep_the_first_collected_at_when_run_twice_over_the_same_input():
    # Arrange
    repository = FakeJobRepository()
    job = build_job()
    use_case = ListJobsUseCase(FakeJobSource([job]), repository)
    first = use_case.execute()

    # Act
    second = use_case.execute()

    # Assert
    assert second[0].collected_at == first[0].collected_at
    assert len(repository.jobs) == 1
