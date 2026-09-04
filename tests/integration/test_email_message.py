import pytest

from job_hunter_ai.domain.errors import InvalidInputError
from job_hunter_ai.infra.appliers.email_message import build_message, render
from tests.fakes import build_job, build_profile


def html_body(message):
    part = message.get_body(("html",))
    assert part is not None
    return part.get_content()


def test_build_message_should_use_the_local_body_and_resolve_its_placeholders(tmp_path):
    # Arrange
    job = build_job(title="Backend Engineer", company="Acme")

    # Act
    message = build_message(job, build_profile(tmp_path))

    # Assert
    body = html_body(message)
    assert "Acme" in body and "Backend Engineer" in body and "Ada Lovelace" in body
    assert "{name}" not in body


def test_build_message_should_fall_back_to_the_example_template_when_the_local_body_is_missing(
    tmp_path,
):
    # Arrange
    fallback = tmp_path / "example.html"
    fallback.write_text("<p>fallback for {company}</p>", encoding="utf-8")
    profile = build_profile(tmp_path, email_body_path=tmp_path / "absent.html")

    # Act
    message = build_message(build_job(), profile, fallback_template=fallback)

    # Assert
    assert "fallback for Acme" in html_body(message)


def test_build_message_should_attach_the_resume_as_a_pdf(tmp_path):
    # Arrange
    profile = build_profile(tmp_path)

    # Act
    message = build_message(build_job(), profile)

    # Assert
    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_filename() == "resume.pdf"


def test_build_message_should_prefer_the_explicit_recipient_over_the_job_address(tmp_path):
    # Arrange
    job = build_job(apply_email="jobs@acme.com")

    # Act
    message = build_message(job, build_profile(tmp_path), recipient="hr@acme.com")

    # Assert
    assert message["To"] == "hr@acme.com"


def test_build_message_should_use_the_job_address_when_no_recipient_is_passed(tmp_path):
    # Arrange
    job = build_job(apply_email="jobs@acme.com")

    # Act
    message = build_message(job, build_profile(tmp_path))

    # Assert
    assert message["To"] == "jobs@acme.com"


def test_build_message_should_raise_invalid_input_when_there_is_no_recipient_at_all(tmp_path):
    # Arrange
    job = build_job(apply_email=None)

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        build_message(job, build_profile(tmp_path))
    assert error.value.code == "INVALID_INPUT"


def test_build_message_should_use_the_explicit_subject_when_it_is_passed(tmp_path):
    # Arrange
    job = build_job()

    # Act
    message = build_message(job, build_profile(tmp_path), subject="Backend role - Ada")

    # Assert
    assert message["Subject"] == "Backend role - Ada"


def test_build_message_should_fall_back_to_the_configured_subject_with_placeholders(tmp_path):
    # Arrange
    job = build_job(title="Backend Engineer")

    # Act
    message = build_message(job, build_profile(tmp_path))

    # Assert
    assert message["Subject"] == "Application - Backend Engineer - Ada Lovelace"


def test_build_message_should_raise_invalid_input_when_the_resume_is_missing(tmp_path):
    # Arrange
    profile = build_profile(tmp_path, resume_path=tmp_path / "absent.pdf")

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        build_message(build_job(), profile)
    assert "resume not found" in str(error.value)


def test_render_should_leave_an_unknown_placeholder_untouched(tmp_path):
    # Arrange
    template = "{title} at {company}, {unknown}"

    # Act
    rendered = render(template, build_job(), build_profile(tmp_path))

    # Assert
    assert rendered == "Backend Engineer at Acme, {unknown}"
