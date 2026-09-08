"""Reads a résumé PDF the way a screening robot does: text only, layout thrown away.

Whatever `pypdf` cannot extract simply does not exist for the score — which is the point
of scoring the real file instead of a curated list of skills.
"""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from job_hunter_ai.domain.entities.resume_document import ResumeDocument
from job_hunter_ai.domain.errors import InvalidInputError, ResumeError

MIN_EXTRACTED_CHARS = 40


class PdfResumeReader:
    """The `ResumeReader` port over a PDF file."""

    name = "pdf"

    def read(self, path: Path) -> ResumeDocument:
        if not path.is_file():
            raise InvalidInputError(f"resume not found: {path}")
        try:
            reader = PdfReader(path)
            pages = [page.extract_text() or "" for page in reader.pages]
        except (PyPdfError, OSError, ValueError) as exc:
            raise ResumeError(f"could not read the resume at {path}: {exc}") from exc
        text = "\n".join(pages).strip()
        if len(text) < MIN_EXTRACTED_CHARS:
            raise ResumeError(
                f"no readable text in {path}: {len(text)} characters extracted from "
                f"{len(pages)} page(s). An image-only PDF scores zero in a real ATS too."
            )
        return ResumeDocument(path=path, text=text, pages=len(pages))
