"""The PDF reader against real files: a readable résumé and an unreadable one."""

from pathlib import Path

import pytest

from job_hunter_ai.domain.errors import InvalidInputError, ResumeError
from job_hunter_ai.infra.resume.pdf_resume_reader import PdfResumeReader

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "resume"


def test_pdf_resume_reader_should_extract_the_text_and_the_page_count_when_the_pdf_has_text():
    # Arrange
    path = FIXTURES / "sample-resume.pdf"

    # Act
    document = PdfResumeReader().read(path)

    # Assert
    assert document.pages == 1
    assert "EXPERIENCIA PROFISSIONAL" in document.text
    assert document.path == path


def test_pdf_resume_reader_should_fail_with_resume_error_when_the_pdf_has_no_readable_text():
    # Arrange
    path = FIXTURES / "unreadable-resume.pdf"

    # Act / Assert
    with pytest.raises(ResumeError) as error:
        PdfResumeReader().read(path)
    assert str(path) in str(error.value)


def test_pdf_resume_reader_should_fail_with_invalid_input_when_the_file_does_not_exist(tmp_path):
    # Arrange
    path = tmp_path / "absent.pdf"

    # Act / Assert
    with pytest.raises(InvalidInputError):
        PdfResumeReader().read(path)


def test_pdf_resume_reader_should_fail_with_resume_error_when_the_file_is_not_a_pdf(tmp_path):
    # Arrange
    path = tmp_path / "resume.pdf"
    path.write_text("this is not a pdf", encoding="utf-8")

    # Act / Assert
    with pytest.raises(ResumeError):
        PdfResumeReader().read(path)
