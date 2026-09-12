"""In-memory `ResumeReader` fake: the use case never touches a real file."""

from pathlib import Path

from job_hunter_ai.domain.entities.resume_document import ResumeDocument


def build_resume(
    text: str = "Python SQL Docker", pages: int = 1, path: Path = Path("resume.pdf")
) -> ResumeDocument:
    return ResumeDocument(path=path, text=text, pages=pages)


class FakeResumeReader:
    name = "fake"

    def __init__(self, document: ResumeDocument | None = None):
        self.document = document or build_resume()
        self.calls: list[Path] = []

    def read(self, path: Path) -> ResumeDocument:
        self.calls.append(path)
        return self.document
