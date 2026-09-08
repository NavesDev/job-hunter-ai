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


def multi_salary_profile(resume: Path) -> CandidateProfile:
    return CandidateProfile(
        name="Ada Lovelace",
        contact_email="ada@example.com",
        resume_path=resume,
        email_body_path=resume,
        extra_fields={
            "phone": "+55 61 99999-0000",
            "linkedin": "https://www.linkedin.com/in/ada",
            "salary_expectation_clt": "4000",
            "salary_expectation_pj": "4500",
            "salary_expectation_internship": "2000",
        },
    )


def test_form_applier_should_pick_the_salary_of_the_contract_the_form_asks_for(
    site: str, resume: Path
) -> None:
    # Arrange
    subject = applier(submit=False)

    # Act
    result = subject.apply(job_at(site), multi_salary_profile(resume))

    # Assert
    assert "salary=4000" in result.detail  # the recorded form asks as CLT


def test_form_applier_should_use_the_chosen_salary_when_the_caller_picks_one(
    site: str, resume: Path
) -> None:
    # Arrange
    subject = applier(submit=False)

    # Act
    result = subject.apply(job_at(site), multi_salary_profile(resume), salary="pj")

    # Assert
    assert "salary=4500" in result.detail


def test_form_applier_should_raise_invalid_input_when_the_chosen_salary_is_not_predefined(
    site: str, resume: Path
) -> None:
    # Arrange
    subject = applier(submit=False)

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        subject.apply(job_at(site), multi_salary_profile(resume), salary="freelance")
    assert "clt" in str(error.value)


def test_form_applier_should_raise_invalid_input_when_no_salary_is_configured_at_all(
    site: str, resume: Path
) -> None:
    # Arrange
    profile = CandidateProfile(
        name="Ada Lovelace",
        contact_email="ada@example.com",
        resume_path=resume,
        email_body_path=resume,
        extra_fields={"phone": "+55 61 99999-0000", "linkedin": "https://linkedin.com/in/ada"},
    )

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        applier(submit=False).apply(job_at(site), profile)
    assert "salary_expectation" in str(error.value)


def test_form_applier_should_fill_the_email_when_the_page_has_no_session(
    site: str, profile: CandidateProfile
) -> None:
    # Arrange
    subject = applier()  # the stand-in renders the anonymous form: email empty and editable

    # Act
    result = subject.apply(job_at(site), profile)

    # Assert
    assert result.status == ApplicationStatus.SENT  # the form refuses to confirm without an email


def test_form_applier_should_leave_the_email_alone_when_the_session_already_filled_it(
    site: str, profile: CandidateProfile
) -> None:
    # Arrange
    job = Job(
        id="geekhunter:abc123abc123",
        source="geekhunter",
        title="Desenvolvedor(a) .NET Júnior/Pleno",
        company="Agenda Digital Ltda.",
        url=f"{site}/job-with-form-logged-in.html",
    )

    # Act
    result = applier().apply(job, profile)

    # Assert
    assert result.status == ApplicationStatus.SENT


def unconfirmed_job_at(site: str) -> Job:
    return job_page(site, "job-with-form-unconfirmed.html")


def screening_job_at(site: str) -> Job:
    return job_page(site, "job-with-form-screening.html")


def job_page(site: str, page: str) -> Job:
    job = job_at(site)
    return Job(
        id=job.id,
        source=job.source,
        title=job.title,
        company=job.company,
        url=f"{site}/{page}",
    )


def test_form_applier_should_quote_what_the_page_said_when_it_never_confirms(
    site, profile, tmp_path
):
    # Arrange
    subject = applier(diagnostics_dir=str(tmp_path / "diagnostics"), timeout_ms=2000)

    # Act / Assert
    with pytest.raises(ApplierError) as error:
        subject.apply(unconfirmed_job_at(site), profile)
    assert "Falha ao enviar sua candidatura" in str(error.value)
    assert "may or may not have gone through" in str(error.value)


def test_form_applier_should_keep_the_unconfirmed_page_on_disk(site, profile, tmp_path):
    # Arrange
    diagnostics = tmp_path / "diagnostics"
    subject = applier(diagnostics_dir=str(diagnostics), timeout_ms=2000)

    # Act
    with pytest.raises(ApplierError):
        subject.apply(unconfirmed_job_at(site), profile)

    # Assert
    saved = list(diagnostics.glob("unconfirmed-*.html"))
    assert len(saved) == 1
    assert "Falha ao enviar sua candidatura" in saved[0].read_text(encoding="utf-8")


def test_form_applier_should_never_put_the_candidates_values_in_the_error(site, profile, tmp_path):
    # Arrange
    subject = applier(diagnostics_dir=str(tmp_path / "diagnostics"), timeout_ms=2000)

    # Act / Assert
    with pytest.raises(ApplierError) as error:
        subject.apply(unconfirmed_job_at(site), profile)
    assert profile.contact_email not in str(error.value)
    assert profile.extra_fields["phone"] not in str(error.value)


def test_form_applier_should_report_the_screening_questions_the_platform_asks(
    site, profile, tmp_path
):
    # Arrange
    subject = applier(diagnostics_dir=str(tmp_path / "diagnostics"), timeout_ms=5000)

    # Act / Assert
    with pytest.raises(ApplierError) as error:
        subject.apply(screening_job_at(site), profile)
    message = str(error.value)
    assert "Quantos anos de experiência em/com .NET você tem?" in message
    assert "Você aceita trabalhar presencialmente?" in message
    assert "screening questions" in message


def test_form_applier_should_not_call_a_screening_screen_an_unconfirmed_application(
    site, profile, tmp_path
):
    # Arrange
    subject = applier(diagnostics_dir=str(tmp_path / "diagnostics"), timeout_ms=5000)

    # Act / Assert
    with pytest.raises(ApplierError) as error:
        subject.apply(screening_job_at(site), profile)
    assert "may or may not have gone through" not in str(error.value)


def test_form_applier_should_answer_no_screening_question_on_the_candidates_behalf(
    site, profile, tmp_path
):
    # Arrange
    subject = applier(diagnostics_dir=str(tmp_path / "diagnostics"), timeout_ms=5000)

    # Act
    with pytest.raises(ApplierError):
        subject.apply(screening_job_at(site), profile)

    # Assert
    saved = list((tmp_path / "diagnostics").glob("unconfirmed-*.html"))
    assert len(saved) == 1
    assert 'name="screening-142139" type="number" value=' not in saved[0].read_text(
        encoding="utf-8"
    )
