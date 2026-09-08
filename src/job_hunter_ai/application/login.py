"""Use case: make sure a platform session exists in the tool's browser profile."""

from job_hunter_ai.domain.entities.session_result import SessionResult
from job_hunter_ai.domain.ports.session_strategy import SessionStrategy


class LoginUseCase:
    """Asks a `SessionStrategy` for a usable session; it decides whether to sign in."""

    def __init__(self, strategy: SessionStrategy) -> None:
        self._strategy = strategy

    def execute(self, force: bool = False) -> SessionResult:
        """Return the session, signing in only when the profile has none — or on `force`."""
        return self._strategy.ensure_session(force=force)
