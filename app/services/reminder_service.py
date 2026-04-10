from __future__ import annotations

import logging

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.services.task_service import TaskService
from app.time_utils import utcnow


logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, session_factory: sessionmaker[Session], settings: Settings) -> None:
        self.session_factory = session_factory
        self.settings = settings

    def process_due_tasks(self) -> None:
        now_utc = utcnow()
        with self.session_factory() as session:
            task_service = TaskService(session, self.settings.default_timezone)
            tasks = task_service.get_due_tasks(now_utc)
            for task in tasks:
                task_service.mark_reminder_sent(task, now_utc)
            session.commit()
            if tasks:
                logger.info("Marked %s due tasks as reminded", len(tasks))
