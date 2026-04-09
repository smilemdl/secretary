from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


UTC = timezone.utc


def utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def get_tz(tz_name: str) -> ZoneInfo:
    return ZoneInfo(tz_name)


def to_utc_naive(local_dt: datetime, tz_name: str) -> datetime:
    tz = get_tz(tz_name)
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(tzinfo=tz)
    return local_dt.astimezone(UTC).replace(tzinfo=None, microsecond=0)


def from_utc_naive(utc_dt: datetime, tz_name: str) -> datetime:
    tz = get_tz(tz_name)
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC)
    return utc_dt.astimezone(tz)


def local_now(tz_name: str) -> datetime:
    return from_utc_naive(utcnow(), tz_name)


def format_user_datetime(utc_dt: datetime | None, tz_name: str) -> str:
    if utc_dt is None:
        return "-"
    return from_utc_naive(utc_dt, tz_name).strftime("%Y-%m-%d %H:%M")


def local_day_bounds_utc(reference_utc: datetime, tz_name: str) -> tuple[datetime, datetime]:
    local_reference = from_utc_naive(reference_utc, tz_name)
    local_start = local_reference.replace(hour=0, minute=0, second=0, microsecond=0)
    local_end = local_start + timedelta(days=1)
    return to_utc_naive(local_start, tz_name), to_utc_naive(local_end, tz_name)
