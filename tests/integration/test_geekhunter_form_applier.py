"""`GeekHunterFormApplier` driving a real browser against a locally served page.

No test here reaches GeekHunter, and none of them submits an application anywhere
but to the local stand-in page described in `tests/fixtures/geekhunter/README.md`.
"""

import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from job_hunter_ai.domain.entities.application_result import ApplicationStatus
from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.errors import ApplierError, InvalidInputError
from job_hunter_ai.infra.appliers.geekhunter_form import GeekHunterFormApplier

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "geekhunter"

pytest.importorskip("playwright", reason="applying through a form needs the `form` extra")


@pytest.fixture(scope="module")
def site() -> Iterator[str]:
    """Serves the recorded pages over HTTP, so the browser sees a real origin."""
    handler = partial(_QuietHandler, directory=str(FIXTURES))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        """Keep the test output pristine."""


@pytest.fixture
def resume(tmp_path: Path) -> Path:
    path: Path = tmp_path / "resume.pdf"
    path.write_bytes(b"%PDF-1.4\n%fake resume for the suite\n")
    return path


@pytest.fixture
def profile(resume: Path) -> CandidateProfile:
    return CandidateProfile(
        name="Ada Lovelace",
        contact_email="ada@example.com",
        resume_path=resume,
        email_body_path=resume,
        extra_fields={
            "phone": "+55 61 99999-0000",
            "linkedin": "https://www.linkedin.com/in/ada",
            "salary_expectation": "8000",
        },
    )


def job_at(site: str) -> Job:
    return Job(
        id="geekhunter:abc123abc123",
        source="geekhunter",
        title="Desenvolvedor(a) .NET Júnior/Pleno",
        company="Agenda Digital Ltda.",
        url=f"{site}/job-with-form.html",
    )


def applier(**settings: object) -> GeekHunterFormApplier:
    return GeekHunterFormApplier({"accept_terms": True, **settings})


def test_form_applier_should_return_sent_when_the_platform_confirms_the_application(site, profile):
    # Arrange
    subject = applier()

    # Act
    result = subject.apply(job_at(site), profile)

    # Assert
    assert result.status == ApplicationStatus.SENT
    assert result.applier == "geekhunter-form"
    assert result.job_id == "geekhunter:abc123abc123"
    assert result.applied_at is not None


def test_form_applier_should_fill_every_field_from_the_profile(site, profile):
    # Arrange
    subject = applier(dry_run=True)

    # Act
    result = subject.apply(job_at(site), profile)

    # Assert
    assert result.status == ApplicationStatus.SKIPPED
    assert "dry run" in result.detail
    assert "Ada Lovelace" in result.detail


def test_form_applier_should_raise_invalid_input_when_the_consent_was_not_configured(site, profile):
    # Arrange
    subject = GeekHunterFormApplier({"accept_terms": False})

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        subject.apply(job_at(site), profile)
    assert "accept_terms" in str(error.value)


def test_form_applier_should_raise_invalid_input_when_a_required_field_is_missing(site, resume):
    # Arrange
    incomplete = CandidateProfile(
        name="Ada Lovelace",
        contact_email="ada@example.com",
        resume_path=resume,
        email_body_path=resume,
        extra_fields={"phone": "+55 61 99999-0000"},
    )

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        applier().apply(job_at(site), incomplete)
    assert "linkedin" in str(error.value)


def test_form_applier_should_raise_invalid_input_when_the_resume_is_missing(
    site, profile, tmp_path
):
    # Arrange
    without_resume = CandidateProfile(
        name=profile.name,
        contact_email=profile.contact_email,
        resume_path=tmp_path / "nowhere.pdf",
        email_body_path=profile.email_body_path,
        extra_fields=profile.extra_fields,
    )

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        applier().apply(job_at(site), without_resume)
    assert "nowhere.pdf" in str(error.value)


def test_form_applier_should_raise_invalid_input_when_the_job_has_no_url(profile):
    # Arrange
    job = Job(id="geekhunter:abc123abc123", source="geekhunter", title="x", company="y", url=None)

    # Act / Assert
    with pytest.raises(InvalidInputError):
        applier().apply(job, profile)


def test_form_applier_should_raise_applier_error_when_the_page_has_no_application_form(
    site, profile
):
    # Arrange
    job = Job(
        id="geekhunter:abc123abc123",
        source="geekhunter",
        title="Desenvolvedor",
        company="Agenda Digital Ltda.",
        url=f"{site}/job-detail-2.html",
    )

    # Act / Assert
    with pytest.raises(ApplierError) as error:
        applier().apply(job, profile)
    assert error.value.code == "APPLIER_ERROR"


def test_form_applier_should_not_require_the_consent_when_it_is_not_going_to_submit(site, profile):
    # Arrange
    subject = GeekHunterFormApplier({"accept_terms": False, "submit": False})

    # Act
    result = subject.apply(job_at(site), profile)

    # Assert
    assert result.status == ApplicationStatus.SKIPPED


def test_form_applier_should_leave_the_terms_unchecked_when_it_is_not_going_to_submit(
    site: str, profile: CandidateProfile
) -> None:
    # Arrange
    subject = GeekHunterFormApplier({"accept_terms": False, "submit": False, "headless": True})

    # Act
    result = subject.apply(job_at(site), profile)

    # Assert
    assert "nothing submitted" in result.detail
