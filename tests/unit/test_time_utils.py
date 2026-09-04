from datetime import UTC, datetime, timedelta, timezone

from job_hunter_ai.domain.time_utils import from_iso_utc, to_iso_utc, utc_now


def test_to_iso_utc_should_render_the_contract_format_when_given_an_aware_datetime():
    # Arrange
    moment = datetime(2026, 9, 3, 14, 0, 0, tzinfo=UTC)

    # Act
    rendered = to_iso_utc(moment)

    # Assert
    assert rendered == "2026-09-03T14:00:00Z"


def test_to_iso_utc_should_convert_to_utc_when_given_another_timezone():
    # Arrange
    moment = datetime(2026, 9, 3, 11, 0, 0, tzinfo=timezone(timedelta(hours=-3)))

    # Act
    rendered = to_iso_utc(moment)

    # Assert
    assert rendered == "2026-09-03T14:00:00Z"


def test_from_iso_utc_should_round_trip_the_value_produced_by_to_iso_utc():
    # Arrange
    original = "2026-09-03T14:00:00Z"

    # Act
    parsed = from_iso_utc(original)

    # Assert
    assert to_iso_utc(parsed) == original


def test_utc_now_should_return_an_aware_datetime_in_utc():
    # Arrange / Act
    moment = utc_now()

    # Assert
    assert moment.tzinfo is not None
    assert moment.utcoffset() == timedelta(0)
