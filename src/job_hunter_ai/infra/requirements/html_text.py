"""Turns the HTML a platform publishes into the blocks a requirements extractor reads.

The stdlib parser is enough here — the descriptions are plain prose with headings and
lists, and no dependency is worth adding for that.

Emphasis is read the way the platforms use it: a paragraph that is emphasized end to end is
a section heading (`<p><strong>Requisitos</strong></p>`), while emphasis inside a sentence
marks the skill itself (`Conhecimento em <strong>Spring Boot</strong>`) — so only the
emphasized part of such a block is kept, and the filler around it is dropped. A list item is
never a heading, however it is styled: a bold bullet is still one of the list's entries.
"""

from html.parser import HTMLParser

TITLES = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
EMPHASIS = frozenset({"strong", "b", "em"})
BLOCKS = frozenset({"li", "p", "div", "br", "tr", "td"})


class _BlockCollector(HTMLParser):
    """Collects `(is_heading, text)` for every block of the document, in reading order."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[tuple[bool, str]] = []
        self._buffer: list[str] = []
        self._emphasized: list[str] = []
        self._title = False
        self._item = False
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in EMPHASIS:
            self._depth += 1
        elif tag in TITLES:
            self.flush()
            self._title = True
        elif tag in BLOCKS:
            self.flush()
            self._item = tag == "li"

    def handle_endtag(self, tag: str) -> None:
        if tag in EMPHASIS:
            self._depth = max(self._depth - 1, 0)
        elif tag in TITLES or tag in BLOCKS:
            self.flush()

    def handle_data(self, data: str) -> None:
        self._buffer.append(data)
        if self._depth:
            self._emphasized.append(data)

    def flush(self) -> None:
        whole = _collapse("".join(self._buffer))
        parts = [_collapse(part) for part in self._emphasized]
        title, self._title = self._title, False
        item, self._item = self._item, False
        self._buffer.clear()
        self._emphasized.clear()
        if not whole:
            return
        emphasized = " ".join(part for part in parts if part)
        if title or (emphasized and emphasized == whole and not item):
            self.blocks.append((True, whole))
        elif emphasized:
            self.blocks.extend((False, part) for part in parts if part)
        else:
            self.blocks.append((False, whole))


def _collapse(text: str) -> str:
    return " ".join(text.split())


def blocks(html: str) -> list[tuple[bool, str]]:
    """Every text block of the document, flagged as a heading or as content."""
    collector = _BlockCollector()
    collector.feed(html)
    collector.close()
    collector.flush()
    return collector.blocks


def to_text(html: str) -> str:
    """The document as plain text, one block per line."""
    return "\n".join(text for _, text in blocks(html))
