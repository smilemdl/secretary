from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    ACTIVE = "ACTIVE"
    AWAITING_ACTION = "AWAITING_ACTION"
    SNOOZED = "SNOOZED"
    OVERDUE = "OVERDUE"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class ClosureMode(str, Enum):
    REQUIRED = "REQUIRED"
    NOTICE_ONLY = "NOTICE_ONLY"


class EventType(str, Enum):
    CREATED = "CREATED"
    REMINDER_SENT = "REMINDER_SENT"
    SNOOZED = "SNOOZED"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    SUMMARY_INCLUDED = "SUMMARY_INCLUDED"
    FAILED_DELIVERY = "FAILED_DELIVERY"


class CommandType(str, Enum):
    CREATE_TASK = "CREATE_TASK"
    LIST_TODAY = "LIST_TODAY"
    LIST_PENDING = "LIST_PENDING"
    COMPLETE_LATEST = "COMPLETE_LATEST"
    CANCEL_LATEST = "CANCEL_LATEST"
    SNOOZE_LATEST = "SNOOZE_LATEST"
    RESCHEDULE_LATEST = "RESCHEDULE_LATEST"
    HELP = "HELP"
    CLARIFY = "CLARIFY"
    UNKNOWN = "UNKNOWN"


@dataclass
class ParsedCommand:
    kind: CommandType
    raw_text: str
    title: str | None = None
    scheduled_at: datetime | None = None
    detail: str | None = None
    minutes: int | None = None
    question: str | None = None
