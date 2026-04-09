from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.domain import ClosureMode, TaskStatus


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_open_id: Mapped[str] = mapped_column(String(128), index=True)
    chat_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text, default="", server_default="")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.ACTIVE.value, index=True)
    closure_mode: Mapped[str] = mapped_column(
        String(32),
        default=ClosureMode.REQUIRED.value,
        server_default=ClosureMode.REQUIRED.value,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_remind_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_reminded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remind_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_from_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai", server_default="Asia/Shanghai")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskEvent(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MessageDedup(Base):
    __tablename__ = "message_dedup"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    result_hash: Mapped[str] = mapped_column(String(128), default="", server_default="")
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class UserSetting(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_open_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai", server_default="Asia/Shanghai")
    quiet_hours_start: Mapped[str] = mapped_column(String(8), default="23:00", server_default="23:00")
    quiet_hours_end: Mapped[str] = mapped_column(String(8), default="08:00", server_default="08:00")
    default_strategy: Mapped[str] = mapped_column(String(32), default="STANDARD", server_default="STANDARD")
