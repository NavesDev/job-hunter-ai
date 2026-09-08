from pathlib import Path

import pytest

from job_hunter_ai.application.score_job import ScoreJobUseCase
from job_hunter_ai.domain.entities.job_requirements import JobRequirements
from job_hunter_ai.domain.errors import InvalidInputError, JobNotFoundError
from job_hunter_ai.domain.matching.ats_scorer import AtsScorer
from tests.fakes import (
    FakeExtractorRegistry,
    FakeJobRepository,
    FakeRequirementsExtractor,
    FakeResumeReader,
    build_job,
    build_resume,
)

RESUME = Path("resume.pdf")


def build_use_case(repository, extractors=None, reader=None):
    return ScoreJobUseCase(
        repository, extractors or FakeExtractorRegistry(), reader or FakeResumeReader(), AtsScorer()
    )


def test_score_job_should_score_the_stored_job_when_the_id_exists():
    # Arrange
    repository = FakeJobRepository()
    job = build_job()
    repository.save_jobs([job])
    reader = FakeResumeReader(build_resume("Desenvolvedor Python com SQL"))

    # Act
    score = build_use_case(repository, reader=reader).execute(job.id, RESUME)

    # Assert
    assert score.job_id == job.id
    assert score.required_skills.matched == ("python",)
    assert reader.calls == [RESUME]


def test_score_job_should_resolve_the_extractor_of_the_job_source_when_it_runs():
    # Arrange
    repository = FakeJobRepository()
    job = build_job(source="geekhunter")
    repository.save_jobs([job])
    extractors = FakeExtractorRegistry(FakeRequirementsExtractor(JobRequirements(required=("Go",))))

    # Act
    build_use_case(repository, extractors=extractors).execute(job.id, RESUME)

    # Assert
    assert extractors.sources == ["geekhunter"]
    assert extractors.extractor.calls == [job]


def test_score_job_should_fail_with_job_not_found_when_the_job_was_never_collected():
    # Arrange
    use_case = build_use_case(FakeJobRepository())

    # Act / Assert
    with pytest.raises(JobNotFoundError):
        use_case.execute("manual:missing", RESUME)


def test_score_job_should_fail_with_invalid_input_when_the_job_id_is_blank():
    # Arrange
    use_case = build_use_case(FakeJobRepository())

    # Act / Assert
    with pytest.raises(InvalidInputError):
        use_case.execute("   ", RESUME)
