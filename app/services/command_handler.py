from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.domain import CommandType, ParsedCommand
from app.services.llm import LLMInterpreter
from app.services.parser import parse_command
from app.services.task_service import TaskService
from app.time_utils import format_user_datetime, local_now


@dataclass
class HandleResult:
    reply_text: str


class CommandHandler:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.task_service = TaskService(session, settings.default_timezone)
        self.llm = LLMInterpreter(settings)

    def handle_message(self, owner_open_id: str, chat_id: str, message_id: str | None, text: str) -> HandleResult:
        now_local = local_now(self.settings.default_timezone)
        command = parse_command(text, self.settings.default_timezone, now_local)

        if command.kind == CommandType.UNKNOWN:
            llm_command = self.llm.parse(text, now_local)
            if llm_command is not None:
                command = llm_command

        reply_text = self._dispatch(command, owner_open_id, chat_id, message_id)
        return HandleResult(reply_text=reply_text)

    def _dispatch(
        self,
        command: ParsedCommand,
        owner_open_id: str,
        chat_id: str,
        message_id: str | None,
    ) -> str:
        if command.kind == CommandType.CREATE_TASK:
            task = self.task_service.create_task(
                owner_open_id=owner_open_id,
                chat_id=chat_id,
                title=command.title or "",
                detail=command.detail or "",
                scheduled_at=command.scheduled_at or datetime.utcnow(),
                created_from_message_id=message_id,
            )
            return f"已创建日程：{format_user_datetime(task.scheduled_at, task.timezone)} {task.title}"

        if command.kind == CommandType.LIST_TODAY:
            tasks = self.task_service.list_today_tasks(owner_open_id, chat_id)
            if not tasks:
                return "今天还没有未完成的日程。"
            lines = ["今日日程："]
            lines.extend(self.task_service.format_task_line(task) for task in tasks)
            return "\n".join(lines)

        if command.kind == CommandType.LIST_PENDING:
            tasks = self.task_service.list_pending_tasks(owner_open_id, chat_id)
            if not tasks:
                return "当前没有未完成的事务。"
            lines = ["未完成事务："]
            lines.extend(self.task_service.format_task_line(task) for task in tasks)
            return "\n".join(lines)

        if command.kind == CommandType.COMPLETE_LATEST:
            task = self.task_service.complete_latest_task(owner_open_id, chat_id)
            if task is None:
                return "我没找到可以完成的事务。"
            return f"已完成：{format_user_datetime(task.scheduled_at, task.timezone)} {task.title}"

        if command.kind == CommandType.CANCEL_LATEST:
            task = self.task_service.cancel_latest_task(owner_open_id, chat_id)
            if task is None:
                return "我没找到可以取消的事务。"
            return f"已取消：{format_user_datetime(task.scheduled_at, task.timezone)} {task.title}"

        if command.kind == CommandType.SNOOZE_LATEST:
            task = self.task_service.snooze_latest_task(
                owner_open_id,
                chat_id,
                minutes=command.minutes,
                scheduled_at=command.scheduled_at,
            )
            if task is None:
                return "我没找到可以延后的事务。"
            return f"已延后提醒到：{format_user_datetime(task.next_remind_at, task.timezone)} {task.title}"

        if command.kind == CommandType.RESCHEDULE_LATEST:
            task = self.task_service.reschedule_latest_task(
                owner_open_id,
                chat_id,
                scheduled_at=command.scheduled_at or datetime.utcnow(),
            )
            if task is None:
                return "我没找到可以改时间的事务。"
            return f"已改期：{format_user_datetime(task.scheduled_at, task.timezone)} {task.title}"

        if command.kind == CommandType.CLARIFY:
            return command.question or "我需要你说得更具体一些。"

        if command.kind == CommandType.HELP:
            return (
                "我目前支持这些指令：\n"
                "- 明天下午3点提醒我交水电费\n"
                "- 今天还有什么\n"
                "- 未完成\n"
                "- 完成\n"
                "- 取消\n"
                "- 15分钟后提醒\n"
                "- 今晚8点提醒\n"
                "- 改到明天9点"
            )

        return command.question or "我暂时没理解这句话，请换一种更明确的说法。"