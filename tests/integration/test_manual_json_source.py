import json

import pytest

from job_hunter_ai.domain.errors import InvalidInputError
from job_hunter_ai.infra.sources.manual_json import ManualJsonJobSource

VALID_ENTRY = {
    "title": "Backend Engineer",
    "company": "Acme",
    "url": "https://acme.com/jobs/1",
    "description": "Python, SQL",
    "apply_email": "jobs@acme.com",
}


def write_jobs(tmp_path, payload):
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_manual_source_should_normalize_every_contract_field_when_the_file_is_valid(tmp_path):
    # Arrange
    path = write_jobs(tmp_path, [VALID_ENTRY])

    # Act
    jobs = ManualJsonJobSource().fetch(max_length=50, file=path)

    # Assert
    job = jobs[0]
    assert job.id.startswith("manual:")
    assert (job.source, job.title, job.company) == ("manual", "Backend Engineer", "Acme")
    assert (job.url, job.apply_email) == (VALID_ENTRY["url"], VALID_ENTRY["apply_email"])
    assert job.raw == VALID_ENTRY
    assert job.collected_at is not None


def test_manual_source_should_produce_the_same_ids_when_read_twice(tmp_path):
    # Arrange
    path = write_jobs(tmp_path, [VALID_ENTRY])
    source = ManualJsonJobSource()

    # Act
    first, second = source.fetch(max_length=50, file=path), source.fetch(max_length=50, file=path)

    # Assert
    assert [job.id for job in first] == [job.id for job in second]


def test_manual_source_should_cap_the_result_when_max_length_is_reached(tmp_path):
    # Arrange
    path = write_jobs(tmp_path, [{**VALID_ENTRY, "url": f"https://acme.com/{i}"} for i in range(4)])

    # Act
    jobs = ManualJsonJobSource().fetch(max_length=2, file=path)

    # Assert
    assert len(jobs) == 2


def test_manual_source_should_raise_invalid_input_when_the_file_does_not_exist(tmp_path):
    # Arrange
    path = tmp_path / "missing.json"

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        ManualJsonJobSource().fetch(max_length=50, file=path)
    assert error.value.code == "INVALID_INPUT"


def test_manual_source_should_raise_invalid_input_when_the_json_is_malformed(tmp_path):
    # Arrange
    path = tmp_path / "jobs.json"
    path.write_text("{not json", encoding="utf-8")

    # Act / Assert
    with pytest.raises(InvalidInputError):
        ManualJsonJobSource().fetch(max_length=50, file=path)


def test_manual_source_should_raise_invalid_input_when_the_payload_is_not_a_list(tmp_path):
    # Arrange
    path = write_jobs(tmp_path, VALID_ENTRY)

    # Act / Assert
    with pytest.raises(InvalidInputError):
        ManualJsonJobSource().fetch(max_length=50, file=path)


def test_manual_source_should_raise_invalid_input_when_a_required_field_is_missing(tmp_path):
    # Arrange
    path = write_jobs(tmp_path, [{"title": "Backend Engineer"}])

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        ManualJsonJobSource().fetch(max_length=50, file=path)
    assert "company" in str(error.value)


def test_manual_source_should_raise_invalid_input_when_the_file_flag_is_absent():
    # Arrange
    source = ManualJsonJobSource()

    # Act / Assert
    with pytest.raises(InvalidInputError):
        source.fetch(max_length=50)
