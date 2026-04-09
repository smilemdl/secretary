from __future__ import annotations

import re
from datetime import datetime, timedelta

from app.domain import CommandType, ParsedCommand
from app.time_utils import local_now, to_utc_naive


WEEKDAY_MAP = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
}


def parse_command(text: str, tz_name: str, now_local: datetime | None = None) -> ParsedCommand:
    raw_text = normalize_text(text)
    if not raw_text:
        return ParsedCommand(kind=CommandType.HELP, raw_text=text)

    now_local = now_local or local_now(tz_name)

    if raw_text in {"帮助", "help", "菜单"}:
        return ParsedCommand(kind=CommandType.HELP, raw_text=text)
    if raw_text in {"今天还有什么", "今日日程", "今天日程"}:
        return ParsedCommand(kind=CommandType.LIST_TODAY, raw_text=text)
    if raw_text in {"未完成", "还有什么没做", "待办"}:
        return ParsedCommand(kind=CommandType.LIST_PENDING, raw_text=text)
    if raw_text == "完成":
        return ParsedCommand(kind=CommandType.COMPLETE_LATEST, raw_text=text)
    if raw_text == "取消":
        return ParsedCommand(kind=CommandType.CANCEL_LATEST, raw_text=text)

    snooze_match = re.fullmatch(r"(\d{1,3})分钟后提醒", raw_text)
    if snooze_match:
        return ParsedCommand(
            kind=CommandType.SNOOZE_LATEST,
            raw_text=text,
            minutes=int(snooze_match.group(1)),
        )

    if raw_text.startswith("改到"):
        time_chunk = raw_text.removeprefix("改到").strip()
        parsed_at = parse_datetime_phrase(time_chunk, tz_name, now_local)
        if parsed_at is None:
            return ParsedCommand(kind=CommandType.CLARIFY, raw_text=text, question="我没看懂新的时间，请换成更明确的说法。")
        return ParsedCommand(kind=CommandType.RESCHEDULE_LATEST, raw_text=text, scheduled_at=parsed_at)

    if raw_text.endswith("提醒"):
        maybe_time = raw_text.removesuffix("提醒").strip()
        parsed_at = parse_datetime_phrase(maybe_time, tz_name, now_local)
        if parsed_at is not None:
            return ParsedCommand(kind=CommandType.SNOOZE_LATEST, raw_text=text, scheduled_at=parsed_at)

    command = _parse_create_task(raw_text, tz_name, now_local)
    if command is not None:
        return command

    return ParsedCommand(
        kind=CommandType.UNKNOWN,
        raw_text=text,
        question="我暂时只支持创建事务、查询今天/未完成，以及完成、取消、延后、改时间。",
    )


def normalize_text(text: str) -> str:
    text = re.sub(r"@_user_\d+\s*", "", text)
    text = text.replace("\u200b", " ").strip()
    return re.sub(r"\s+", "", text)


def parse_datetime_phrase(text: str, tz_name: str, now_local: datetime | None = None) -> datetime | None:
    now_local = now_local or local_now(tz_name)
    day_match = _match_day_phrase(text, now_local)
    if day_match is None:
        return None

    target_day, rest = day_match
    time_match = re.search(r"(上午|中午|下午|晚上|今晚)?(\d{1,2})(?:[:点时](\d{1,2}))?(半|分)?", rest)
    if time_match is None:
        return None

    period = time_match.group(1) or ""
    hour = int(time_match.group(2))
    minute_token = time_match.group(3)
    suffix = time_match.group(4) or ""

    minute = int(minute_token) if minute_token else 0
    if suffix == "半" and minute_token is None:
        minute = 30

    if period in {"下午", "晚上", "今晚"} and hour < 12:
        hour += 12
    if period == "中午" and hour < 11:
        hour += 12

    local_dt = target_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local_dt < now_local:
        return None
    return to_utc_naive(local_dt, tz_name)


def _parse_create_task(raw_text: str, tz_name: str, now_local: datetime) -> ParsedCommand | None:
    patterns = [
        re.compile(r"(?P<time>.+?)提醒我(?P<title>.+)"),
        re.compile(r"提醒我(?P<time>.+?)(?P<title>.+)"),
    ]
    for pattern in patterns:
        match = pattern.fullmatch(raw_text)
        if match is None:
            continue
        parsed_at = parse_datetime_phrase(match.group("time"), tz_name, now_local)
        title = match.group("title").strip()
        if parsed_at is None or not title:
            return ParsedCommand(kind=CommandType.CLARIFY, raw_text=raw_text, question="我没看懂时间或事务内容，请再说得更明确一点。")
        return ParsedCommand(
            kind=CommandType.CREATE_TASK,
            raw_text=raw_text,
            title=title,
            scheduled_at=parsed_at,
        )
    return None


def _match_day_phrase(text: str, now_local: datetime) -> tuple[datetime, str] | None:
    candidates = {
        "今天": 0,
        "明天": 1,
        "后天": 2,
        "今晚": 0,
    }
    for prefix, offset in candidates.items():
        if text.startswith(prefix):
            target = (now_local + timedelta(days=offset)).replace(second=0, microsecond=0)
            rest = text[len(prefix) :]
            if prefix == "今晚" and not rest.startswith("晚上"):
                rest = "晚上" + rest
            return target, rest

    weekday_match = re.match(r"(下周|这周|周)([一二三四五六日天])", text)
    if weekday_match:
        label, weekday_token = weekday_match.groups()
        weekday = WEEKDAY_MAP[weekday_token]
        current_weekday = now_local.weekday()
        delta = (weekday - current_weekday) % 7
        if label == "下周":
            delta += 7 if delta > 0 else 14
        elif delta == 0:
            delta = 7
        target = (now_local + timedelta(days=delta)).replace(second=0, microsecond=0)
        return target, text[weekday_match.end() :]

    return None