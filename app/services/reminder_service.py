from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.services.feishu import FeishuClient
from app.services.task_service import TaskService
from app.time_utils import format_user_datetime, utcnow


logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, session_factory: sessionmaker[Session], feishu_client: FeishuClient, settings: Settings) -> None:
        self.session_factory = session_factory
        self.feishu_client = feishu_client
        self.settings = settings

    def process_due_tasks(self) -> None:
        now_utc = utcnow()
        with self.session_factory() as session:
            task_service = TaskService(session, self.settings.default_timezone)
            tasks = task_service.get_due_tasks(now_utc)
            for task in tasks:
                message = self._build_reminder_text(task)
                try:
                    sent = self.feishu_client.send_text(task.chat_id, message)
                except Exception:
                    logger.exception("Failed to send reminder for task %s", task.id)
                    continue
                if sent:
                    task_service.mark_reminder_sent(task, now_utc)
            session.commit()

    def send_evening_summary(self) -> None:
        self._send_summary(only_overdue=False, title="今日未完成事务")

    def send_overdue_summary(self) -> None:
        self._send_summary(only_overdue=True, title="逾期事务汇总")

    def _send_summary(self, only_overdue: bool, title: str) -> None:
        now_utc = utcnow()
        with self.session_factory() as session:
            task_service = TaskService(session, self.settings.default_timezone)
            tasks = task_service.get_overdue_tasks(now_utc) if only_overdue else task_service.get_open_tasks()
            grouped: dict[tuple[str, str], list] = defaultdict(list)
            for task in tasks:
                grouped[(task.chat_id, task.owner_open_id)].append(task)

            for (chat_id, _owner_open_id), chat_tasks in grouped.items():
                if not chat_tasks:
                    continue
                lines = [title]
                for index, task in enumerate(chat_tasks, start=1):
                    lines.append(f"{index}. {format_user_datetime(task.scheduled_at, task.timezone)} {task.title} [{task.status}]")
                lines.append("可回复：完成 / 15分钟后提醒 / 改到明天9点 / 取消")
                try:
                    self.feishu_client.send_text(chat_id, "\n".join(lines))
                except Exception:
                    logger.exception("Failed to send summary to chat %s", chat_id)
            session.commit()

    def _build_reminder_text(self, task) -> str:
        return (
            f"现在该处理：{task.title}\n"
            f"时间：{format_user_datetime(task.scheduled_at, task.timezone)}\n"
            "回复：完成 / 15分钟后提醒 / 今晚8点提醒 / 改到明天9点 / 取消"
        )