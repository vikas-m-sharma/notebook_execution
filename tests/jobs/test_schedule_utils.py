from datetime import datetime, timezone
import pytest

from app.jobs.exceptions import ScheduleValidationError
from app.jobs.schedule_utils import calculate_next_run, validate_cron_expression, validate_timezone


def test_validate_timezone():
    """Verify timezone validation for valid and invalid ZoneInfo identifiers."""
    assert validate_timezone("UTC") is True
    assert validate_timezone("Asia/Kolkata") is True
    assert validate_timezone("America/New_York") is True
    assert validate_timezone("Invalid/NonExistent_TZ") is False
    assert validate_timezone("") is False


def test_validate_cron_expression():
    """Verify 5-field cron expression syntax validation."""
    assert validate_cron_expression("0 2 * * *") is True
    assert validate_cron_expression("*/5 * * * *") is True
    assert validate_cron_expression("0 0 1 1 *") is True
    assert validate_cron_expression("invalid_cron") is False
    assert validate_cron_expression("0 2 * *") is False  # Only 4 fields


def test_calculate_next_run():
    """Verify next run timestamp calculation in target timezone."""
    now = datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc)

    next_run = calculate_next_run("*/5 * * * *", "Asia/Kolkata", base_time=now)
    assert next_run is not None
    assert next_run > now

    with pytest.raises(ScheduleValidationError):
        calculate_next_run("invalid_cron", "UTC")

    with pytest.raises(ScheduleValidationError):
        calculate_next_run("0 2 * * *", "Invalid/TZ")
