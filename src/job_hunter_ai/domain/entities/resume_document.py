from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ResumeDocument:
    """A résumé as a machine sees it: the text a parser managed to pull out of the file.

    `pages` and `text` together are what makes the format score possible — a file whose
    pages yield almost no text is the "resume as an image" an ATS cannot read.
    """

    path: Path
    text: str
    pages: int = 1
