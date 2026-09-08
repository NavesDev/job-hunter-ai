"""`GeekHunterJobSource` against recorded pages. Nothing here touches the network."""

import pytest

from job_hunter_ai.domain.errors import InvalidInputError, SourceError
from job_hunter_ai.domain.job_id import build_job_id
from job_hunter_ai.domain.time_utils import utc_now
from job_hunter_ai.infra.sources.geekhunter import GeekHunterJobSource
from tests.fakes.http_client import (
    LISTING,
    FakeHttpClient,
    client_over_both_listings,
    fixture,
    listed_urls,
    recorded_client,
)


def source_over(client: FakeHttpClient) -> GeekHunterJobSource:
    return GeekHunterJobSource(client)


FIRST_JOB_URL = "https://www.geekhunter.com/pt/code-group/jobs/analista-de-sistemas-pleno-senior--4"
FIRST_JOB_IDENTIFIER = "c1372dc3f8f7efcc1fbad13e64835a14ce9a7d15b1ba20c9f026d7a28dcdeebf"


def test_geekhunter_source_should_map_every_contract_field_when_the_pages_are_valid():
    # Arrange
    source = GeekHunterJobSource(recorded_client())

    # Act
    jobs = source.fetch(max_length=1)

    # Assert
    job = jobs[0]
    assert (job.source, job.title, job.company) == (
        "geekhunter",
        "Analista de Sistemas Pleno/Sênior",
        "Code Group",
    )
    assert job.url == FIRST_JOB_URL
    assert job.description.startswith("<p><strong>Requisitos</strong></p>")
    assert job.collected_at is not None


def test_geekhunter_source_should_never_expose_an_apply_email_because_the_platform_has_none():
    # Arrange
    source = GeekHunterJobSource(recorded_client())

    # Act
    jobs = source.fetch(max_length=3)

    # Assert
    assert [job.apply_email for job in jobs] == [None, None, None]


def test_geekhunter_source_should_keep_the_whole_json_ld_payload_in_raw():
    # Arrange
    source = GeekHunterJobSource(recorded_client())

    # Act
    job = source.fetch(max_length=1)[0]

    # Assert
    assert job.raw["identifier"]["value"] == FIRST_JOB_IDENTIFIER
    assert job.raw["skills"]
    assert job.raw["datePosted"] == "2026-09-04"


def test_geekhunter_source_should_derive_the_id_from_the_platform_identifier():
    # Arrange
    source = GeekHunterJobSource(recorded_client())

    # Act
    job = source.fetch(max_length=1)[0]

    # Assert
    assert job.id == build_job_id("geekhunter", external_id=FIRST_JOB_IDENTIFIER)


def test_geekhunter_source_should_produce_the_same_ids_when_fetched_twice():
    # Arrange
    source = GeekHunterJobSource(recorded_client())

    # Act
    first, second = source.fetch(max_length=3), source.fetch(max_length=3)

    # Assert
    assert [job.id for job in first] == [job.id for job in second]


def test_geekhunter_source_should_stop_at_max_length_without_fetching_further_details():
    # Arrange
    client = recorded_client()
    source = GeekHunterJobSource(client)

    # Act
    jobs = source.fetch(max_length=2)

    # Assert
    assert len(jobs) == 2
    assert client.requested == [f"{LISTING}?page=1", *listed_urls("listing-page-1.html")[:2]]


def test_geekhunter_source_should_follow_pagination_when_one_page_is_not_enough():
    # Arrange
    client = client_over_both_listings()
    source = GeekHunterJobSource(client)

    # Act
    jobs = source.fetch(max_length=11)

    # Assert
    assert len(jobs) == 11
    listing_requests = [url for url in client.requested if url.startswith(f"{LISTING}?")]
    assert listing_requests == [f"{LISTING}?page=1", f"{LISTING}?page=2"]


def test_geekhunter_source_should_apply_the_configured_filters_to_the_listing_url():
    # Arrange
    client = recorded_client(
        **{
            f"{LISTING}?page=1&experienceLevel=senior&workModality=remote": fixture(
                "listing-page-1.html"
            )
        }
    )
    settings = {"filters": {"workModality": "remote", "experienceLevel": "senior"}}
    source = GeekHunterJobSource(client, settings=settings)

    # Act
    source.fetch(max_length=1)

    # Assert
    assert client.requested[0] == (f"{LISTING}?page=1&experienceLevel=senior&workModality=remote")


def test_geekhunter_source_should_raise_invalid_input_when_a_filter_value_is_unknown():
    # Arrange
    client = recorded_client()

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        GeekHunterJobSource(client, settings={"filters": {"workModality": "in_person"}})
    assert "in_person" in str(error.value)
    assert client.requested == []  # nothing is requested with a filter the platform ignores


def test_geekhunter_source_should_raise_invalid_input_when_a_filter_name_is_unknown():
    # Arrange
    client = recorded_client()

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        GeekHunterJobSource(client, settings={"filters": {"seniority": "senior"}})
    assert "seniority" in str(error.value)


def test_geekhunter_source_should_raise_source_error_when_the_listing_returns_no_job():
    # Arrange
    client = FakeHttpClient({f"{LISTING}?page=1": fixture("listing-empty.html")})
    source = GeekHunterJobSource(client)

    # Act / Assert
    with pytest.raises(SourceError) as error:
        source.fetch(max_length=5)
    assert error.value.code == "SOURCE_ERROR"


def test_geekhunter_source_should_raise_source_error_when_a_detail_page_lost_its_json_ld():
    # Arrange
    client = recorded_client()
    client.pages[FIRST_JOB_URL] = fixture("job-detail-without-json-ld.html")
    source = GeekHunterJobSource(client)

    # Act / Assert
    with pytest.raises(SourceError) as error:
        source.fetch(max_length=1)
    assert FIRST_JOB_URL in str(error.value)


def test_geekhunter_source_should_raise_source_error_when_the_listing_lost_its_json_ld():
    # Arrange
    client = FakeHttpClient({f"{LISTING}?page=1": "<html><body>no structured data</body></html>"})
    source = GeekHunterJobSource(client)

    # Act / Assert
    with pytest.raises(SourceError):
        source.fetch(max_length=1)


def test_geekhunter_source_should_use_the_fetch_filters_instead_of_the_configured_ones():
    # Arrange
    client = recorded_client(
        **{f"{LISTING}?page=1&searchTerm=python": fixture("listing-page-1.html")}
    )
    settings = {"filters": {"workModality": "remote", "experienceLevel": "senior"}}
    source = GeekHunterJobSource(client, settings=settings)

    # Act
    source.fetch(max_length=1, filters={"searchTerm": "python"})

    # Assert
    assert client.requested[0] == f"{LISTING}?page=1&searchTerm=python"


def test_geekhunter_source_should_keep_the_configured_filters_when_fetch_carries_none():
    # Arrange
    client = recorded_client(
        **{f"{LISTING}?page=1&experienceLevel=senior": fixture("listing-page-1.html")}
    )
    source = GeekHunterJobSource(client, settings={"filters": {"experienceLevel": "senior"}})

    # Act
    source.fetch(max_length=1, filters={})

    # Assert
    assert client.requested[0] == f"{LISTING}?page=1&experienceLevel=senior"


def test_geekhunter_source_should_raise_invalid_input_when_a_fetch_filter_is_unknown():
    # Arrange
    client = recorded_client()
    source = GeekHunterJobSource(client)

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        source.fetch(max_length=1, filters={"seniority": "senior"})
    assert "seniority" in str(error.value)
    assert client.requested == []


def test_geekhunter_source_should_return_what_it_collected_when_the_listing_ends_early():
    # Arrange
    client = client_over_both_listings()
    client.missing = frozenset({f"{LISTING}?page=2"})

    # Act
    jobs = source_over(client).fetch(max_length=25)

    # Assert
    assert len(jobs) == 10  # the single page the filtered listing had
    assert f"{LISTING}?page=2" in client.requested


def test_geekhunter_source_should_raise_source_error_when_the_listing_itself_is_gone():
    # Arrange
    client = client_over_both_listings()
    client.missing = frozenset({f"{LISTING}?page=1"})

    # Act / Assert
    with pytest.raises(SourceError) as error:
        source_over(client).fetch(max_length=3)
    assert "404" in str(error.value)


def test_geekhunter_source_should_record_the_screening_questions_the_job_asks():
    # Arrange
    url = "https://www.geekhunter.com/pt/code-group/jobs/screening"
    client = recorded_client(**{url: fixture("job-screening-questions.html")})
    client.pages[f"{LISTING}?page=1"] = fixture("listing-page-1.html")
    source = GeekHunterJobSource(client)

    # Act
    job = source._job(url, utc_now())  # the detail page alone: the listing is not the point

    # Assert
    questions = job.raw["screeningQuestions"]
    assert [question["id"] for question in questions] == [142139]
    assert questions[0]["answerType"] == "number"
    assert questions[0]["mandatory"] is True


def test_geekhunter_source_should_record_no_screening_question_when_the_job_asks_none():
    # Arrange
    source = GeekHunterJobSource(recorded_client())

    # Act
    jobs = source.fetch(max_length=1)

    # Assert
    assert jobs[0].raw["screeningQuestions"] == []
