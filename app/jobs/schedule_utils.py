import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.jobs.exceptions import ScheduleValidationError


def validate_timezone(tz_name: str) -> bool:
    """Validate timezone name against Python zoneinfo database."""
    if not tz_name:
        return False
    try:
        ZoneInfo(tz_name)
        return True
    except ZoneInfoNotFoundError:
        return False


def validate_cron_expression(cron_str: str) -> bool:
    """Validate standard 5-field cron expression syntax (minute, hour, dom, month, dow)."""
    if not cron_str:
        return False

    parts = cron_str.strip().split()
    if len(parts) != 5:
        return False

    # Regex matching standard cron fields: *, numbers, ranges (1-5), steps (*/5), lists (1,2,3)
    field_pattern = re.compile(r"^(\*|[0-9]+(-[0-9]+)?)(/[0-9]+)?(,[0-9]+(-[0-9]+)?(/[0-9]+)?)*$")
    for part in parts:
        if not field_pattern.match(part):
            return False

    return True


def calculate_next_run(
    cron_str: Optional[str],
    tz_name: str = "UTC",
    base_time: Optional[datetime] = None,
) -> Optional[datetime]:
    """Calculate the next execution timestamp given a 5-part cron expression and target timezone."""
    if not cron_str:
        return None

    if not validate_timezone(tz_name):
        raise ScheduleValidationError(f"Invalid timezone identifier '{tz_name}'.")

    if not validate_cron_expression(cron_str):
        raise ScheduleValidationError(f"Invalid 5-part cron expression '{cron_str}'.")

    tz = ZoneInfo(tz_name)
    now_in_tz = base_time or datetime.now(tz)
    if now_in_tz.tzinfo is None:
        now_in_tz = now_in_tz.replace(tzinfo=tz)

    parts = cron_str.strip().split()
    minute_spec, hour_spec, dom_spec, month_spec, dow_spec = parts

    # Minute step calculation fallback
    step_minutes = 1
    if "/" in minute_spec:
        try:
            step_minutes = int(minute_spec.split("/")[1])
        except (ValueError, IndexError):
            step_minutes = 1
    elif minute_spec != "*":
        try:
            step_minutes = max(1, int(minute_spec.split(",")[0]))
        except ValueError:
            step_minutes = 1

    next_time = now_in_tz + timedelta(minutes=step_minutes)
    return next_time
