from typing import Protocol

from job_hunter_ai.domain.entities.session_result import SessionResult


class SessionStrategy(Protocol):
    """Keeps a platform session alive in a browser profile. One per platform."""

    name: str

    def ensure_session(self, force: bool = False) -> SessionResult:
        """Return a usable session, logging in only when there is none (or `force`)."""
        ...
