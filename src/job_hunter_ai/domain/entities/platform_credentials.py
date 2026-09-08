"""A platform's login credentials, kept out of every message that could escape.

The password never reaches a repr, a log or an error: the only place it exists in the
open is the browser field it is typed into (docs/ARCHITECTURE.md#configuration-vs-credentials).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformCredentials:
    """The username and password of one platform, loaded from `.env`."""

    platform: str
    username: str
    password: str

    def __repr__(self) -> str:
        """Never print the password — a traceback is not a place for a credential."""
        return f"PlatformCredentials(platform={self.platform!r}, username={self.username!r})"

    def scrub(self, text: str) -> str:
        """The text with the password taken out, for anything that leaves this process."""
        return text.replace(self.password, "***") if self.password else text
