import pytest

from job_hunter_ai.domain.job_id import HASH_LENGTH, build_job_id


def test_build_job_id_should_be_deterministic_when_called_twice_with_the_same_input():
    # Arrange
    kwargs = {"url": "https://acme.com/jobs/1"}

    # Act
    ids = [build_job_id("manual", **kwargs) for _ in range(2)]

    # Assert
    assert ids[0] == ids[1]


def test_build_job_id_should_prefix_with_the_source_and_a_12_char_hash():
    # Arrange
    source = "manual"

    # Act
    job_id = build_job_id(source, url="https://acme.com/jobs/1")

    # Assert
    prefix, digest = job_id.split(":")
    assert prefix == source
    assert len(digest) == HASH_LENGTH


def test_build_job_id_should_prefer_external_id_over_url_and_company_title():
    # Arrange
    common = {"url": "https://acme.com/jobs/1", "company": "Acme", "title": "Backend"}

    # Act
    with_external = build_job_id("manual", external_id="abc-1", **common)
    without_external = build_job_id("manual", **common)

    # Assert
    assert with_external != without_external
    assert with_external == build_job_id("manual", external_id="abc-1")


def test_build_job_id_should_fall_back_to_company_and_title_when_no_url_is_given():
    # Arrange
    fields = {"company": "Acme", "title": "Backend Engineer"}

    # Act
    job_id = build_job_id("manual", **fields)

    # Assert
    assert job_id == build_job_id("manual", company="  ACME ", title="backend engineer")


def test_build_job_id_should_ignore_case_and_surrounding_spaces_in_the_natural_key():
    # Arrange
    url = "https://acme.com/jobs/1"

    # Act
    job_id = build_job_id("manual", url=f"  {url.upper()} ")

    # Assert
    assert job_id == build_job_id("manual", url=url)


def test_build_job_id_should_separate_sources_sharing_the_same_natural_key():
    # Arrange
    url = "https://acme.com/jobs/1"

    # Act
    manual = build_job_id("manual", url=url)
    linkedin = build_job_id("linkedin", url=url)

    # Assert
    assert manual != linkedin


def test_build_job_id_should_raise_when_no_natural_key_is_available():
    # Arrange
    fields = {"company": "Acme"}

    # Act / Assert
    with pytest.raises(ValueError):
        build_job_id("manual", **fields)
