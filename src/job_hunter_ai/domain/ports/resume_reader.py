from pathlib import Path
from typing import Protocol

from job_hunter_ai.domain.entities.resume_document import ResumeDocument


class ResumeReader(Protocol):
    """Turns a résumé file into the text a screening robot would extract from it."""

    def read(self, path: Path) -> ResumeDocument: ...
