"""`LoginUseCase`: it asks the strategy for a session and reports what it answered."""

from job_hunter_ai.application.login import LoginUseCase
from job_hunter_ai.domain.entities.session_result import SessionResult, SessionStatus


class FakeSessionStrategy:
    name = "fake"

    def __init__(self, status=SessionStatus.AUTHENTICATED):
        self.status = status
        self.calls: list[bool] = []

    def ensure_session(self, force: bool = False) -> SessionResult:
        self.calls.append(force)
        return SessionResult(
            source=self.name, status=self.status, profile_dir="/tmp/profile", detail="fake"
        )


def test_login_should_return_what_the_strategy_answered():
    # Arrange
    strategy = FakeSessionStrategy(SessionStatus.ALREADY_AUTHENTICATED)

    # Act
    result = LoginUseCase(strategy).execute()

    # Assert
    assert result.status is SessionStatus.ALREADY_AUTHENTICATED
    assert result.source == "fake"


def test_login_should_forward_force_to_the_strategy():
    # Arrange
    strategy = FakeSessionStrategy()

    # Act
    LoginUseCase(strategy).execute(force=True)

    # Assert
    assert strategy.calls == [True]
