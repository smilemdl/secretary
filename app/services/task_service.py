from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ClosureMode, EventType, TaskStatus
from app.models import Task, TaskEvent
from app.time_utils import format_user_datetime, local_day_bounds_utc, utcnow


ACTIONABLE_STATUSES = [
    TaskStatus.ACTIVE.value,
    TaskStatus.AWAITING_ACTION.value,
    TaskStatus.SNOOZED.value,
    TaskStatus.OVERDUE.value,
]


class TaskService:
    def __init__(self, session: Session, default_timezone: str) -> None:
        self.session = session
        self.default_timezone = default_timezone

    def create_task(
        self,
        owner_open_id: str,
        chat_id: str,
        title: str,
        scheduled_at: datetime,
        detail: str = "",
        closure_mode: ClosureMode = ClosureMode.REQUIRED,
        created_from_message_id: str | None = None,
    ) -> Task:
        task = Task(
            owner_open_id=owner_open_id,
            chat_id=chat_id,
            title=title,
            detail=detail,
            scheduled_at=scheduled_at,
            status=TaskStatus.ACTIVE.value,
            closure_mode=closure_mode.value,
            next_remind_at=scheduled_at,
            created_from_message_id=created_from_message_id,
            timezone=self.default_timezone,
        )
        self.session.add(task)
        self.session.flush()
        self._record_event(task.id, EventType.CREATED, {"title": title, "scheduled_at": scheduled_at.isoformat()})
        return task

    def list_today_tasks(self, owner_open_id: str, chat_id: str, now_utc: datetime | None = None) -> list[Task]:
        now_utc = now_utc or utcnow()
        day_start, day_end = local_day_bounds_utc(now_utc, self.default_timezone)
        stmt = (
            select(Task)
            .where(
                Task.owner_open_id == owner_open_id,
                Task.chat_id == chat_id,
                Task.scheduled_at >= day_start,
                Task.scheduled_at < day_end,
                Task.status.in_(ACTIONABLE_STATUSES),
            )
            .order_by(Task.scheduled_at.asc())
        )
        return list(self.session.scalars(stmt))

    def list_pending_tasks(self, owner_open_id: str, chat_id: str) -> list[Task]:
        stmt = (
            select(Task)
            .where(
                Task.owner_open_id == owner_open_id,
                Task.chat_id == chat_id,
                Task.status.in_(ACTIONABLE_STATUSES),
            )
            .order_by(Task.scheduled_at.asc())
        )
        return list(self.session.scalars(stmt))

    def complete_latest_task(self, owner_open_id: str, chat_id: str) -> Task | None:
        task = self._get_latest_actionable_task(owner_open_id, chat_id)
        if task is None:
            return None
        task.status = TaskStatus.DONE.value
        task.completed_at = utcnow()
        task.next_remind_at = None
        self._record_event(task.id, EventType.COMPLETED, {})
        return task

    def cancel_latest_task(self, owner_open_id: str, chat_id: str) -> Task | None:
        task = self._get_latest_actionable_task(owner_open_id, chat_id)
        if task is None:
            return None
        task.status = TaskStatus.CANCELLED.value
        task.cancelled_at = utcnow()
        task.next_remind_at = None
        self._record_event(task.id, EventType.CANCELLED, {})
        return task

    def snooze_latest_task(
        self,
        owner_open_id: str,
        chat_id: str,
        minutes: int | None = None,
        scheduled_at: datetime | None = None,
    ) -> Task | None:
        task = self._get_latest_actionable_task(owner_open_id, chat_id)
        if task is None:
            return None

        now_utc = utcnow()
        if scheduled_at is None:
            if minutes is None:
                minutes = 15
            scheduled_at = now_utc + timedelta(minutes=minutes)

        task.status = TaskStatus.SNOOZED.value
        task.next_remind_at = scheduled_at
        self._record_event(
            task.id,
            EventType.SNOOZED,
            {"next_remind_at": scheduled_at.isoformat(), "minutes": minutes},
        )
        return task

    def reschedule_latest_task(self, owner_open_id: str, chat_id: str, scheduled_at: datetime) -> Task | None:
        task = self._get_latest_actionable_task(owner_open_id, chat_id)
        if task is None:
            return None
        task.status = TaskStatus.SNOOZED.value
        task.scheduled_at = scheduled_at
        task.next_remind_at = scheduled_at
        self._record_event(task.id, EventType.RESCHEDULED, {"scheduled_at": scheduled_at.isoformat()})
        return task

    def get_due_tasks(self, now_utc: datetime | None = None) -> list[Task]:
        now_utc = now_utc or utcnow()
        stmt = (
            select(Task)
            .where(
                Task.status.in_(ACTIONABLE_STATUSES),
                Task.next_remind_at.is_not(None),
                Task.next_remind_at <= now_utc,
            )
            .order_by(Task.next_remind_at.asc(), Task.id.asc())
        )
        return list(self.session.scalars(stmt))

    def get_open_tasks(self) -> list[Task]:
        stmt = select(Task).where(Task.status.in_(ACTIONABLE_STATUSES)).order_by(Task.chat_id.asc(), Task.scheduled_at.asc())
        return list(self.session.scalars(stmt))

    def get_overdue_tasks(self, now_utc: datetime | None = None) -> list[Task]:
        now_utc = now_utc or utcnow()
        stmt = (
            select(Task)
            .where(
                Task.status.in_(ACTIONABLE_STATUSES),
                Task.scheduled_at < now_utc,
            )
            .order_by(Task.chat_id.asc(), Task.scheduled_at.asc())
        )
        return list(self.session.scalars(stmt))

    def mark_reminder_sent(self, task: Task, sent_at: datetime | None = None) -> None:
        sent_at = sent_at or utcnow()
        task.last_reminded_at = sent_at
        task.remind_count += 1

        if task.status in {TaskStatus.ACTIVE.value, TaskStatus.SNOOZED.value}:
            task.status = TaskStatus.AWAITING_ACTION.value

        if task.closure_mode == ClosureMode.NOTICE_ONLY.value:
            task.status = TaskStatus.DONE.value
            task.completed_at = sent_at
            task.next_remind_at = None
        elif task.remind_count == 1:
            task.next_remind_at = sent_at + timedelta(minutes=15)
        elif task.remind_count == 2:
            task.next_remind_at = sent_at + timedelta(hours=2)
        else:
            task.status = TaskStatus.OVERDUE.value
            task.next_remind_at = None

        self._record_event(task.id, EventType.REMINDER_SENT, {"sent_at": sent_at.isoformat()})

    def format_task_line(self, task: Task) -> str:
        return f"- {format_user_datetime(task.scheduled_at, task.timezone)} {task.title} [{task.status}]"

    def _get_latest_actionable_task(self, owner_open_id: str, chat_id: str) -> Task | None:
        stmt = (
            select(Task)
            .where(
                Task.owner_open_id == owner_open_id,
                Task.chat_id == chat_id,
                Task.status.in_(ACTIONABLE_STATUSES),
            )
            .order_by(Task.last_reminded_at.desc(), Task.scheduled_at.desc(), Task.id.desc())
        )
        return self.session.scalar(stmt)

    def _record_event(self, task_id: int, event_type: EventType, payload: dict[str, object]) -> None:
        event = TaskEvent(task_id=task_id, event_type=event_type.value, payload=json.dumps(payload, ensure_ascii=False))
        self.session.add(event)