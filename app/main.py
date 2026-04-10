from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal, get_session, init_db
from app.services.command_handler import CommandHandler
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService
from app.time_utils import utcnow


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


class CommandRequest(BaseModel):
    text: str


def _build_scheduler(settings: Settings) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=settings.default_timezone)
    reminder_service = ReminderService(SessionLocal, settings)
    scheduler.add_job(
        reminder_service.process_due_tasks,
        "interval",
        seconds=settings.reminder_scan_interval_seconds,
        id="scan_due_tasks",
        replace_existing=True,
    )
    return scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()
    scheduler = _build_scheduler(settings)
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduler started")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/state")
def get_state(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return _build_state_payload(session, settings)


@app.post("/api/commands")
def execute_command(
    payload: CommandRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    handler = CommandHandler(session, settings)
    result = handler.handle_command(
        owner_id=settings.default_owner_id,
        context_id=settings.default_context_id,
        request_id=None,
        text=payload.text,
    )
    session.commit()
    return {
        "reply_text": result.reply_text,
        "state": _build_state_payload(session, settings),
    }


def _build_state_payload(session: Session, settings: Settings) -> dict[str, object]:
    task_service = TaskService(session, settings.default_timezone)
    _refresh_due_tasks(task_service)
    current_tasks = task_service.list_current_tasks(settings.default_owner_id, settings.default_context_id)
    today_tasks = task_service.list_today_tasks(settings.default_owner_id, settings.default_context_id)
    pending_tasks = task_service.list_pending_tasks(settings.default_owner_id, settings.default_context_id)
    overdue_tasks = task_service.list_overdue_tasks(settings.default_owner_id, settings.default_context_id)

    focus_task = task_service.serialize_task(current_tasks[0]) if current_tasks else None
    summary = {
        "today_count": len(today_tasks),
        "pending_count": len(pending_tasks),
        "overdue_count": len(overdue_tasks),
    }

    return {
        "server_time": utcnow().isoformat(),
        "poll_interval_seconds": settings.web_poll_interval_seconds,
        "focus_task": focus_task,
        "current_tasks": [task_service.serialize_task(task) for task in current_tasks],
        "today_tasks": [task_service.serialize_task(task) for task in today_tasks],
        "pending_tasks": [task_service.serialize_task(task) for task in pending_tasks],
        "overdue_tasks": [task_service.serialize_task(task) for task in overdue_tasks],
        "summary": summary,
    }


def _refresh_due_tasks(task_service: TaskService) -> None:
    now_utc = utcnow()
    due_tasks = task_service.get_due_tasks(now_utc)
    for task in due_tasks:
        task_service.mark_reminder_sent(task, now_utc)
    if due_tasks:
        task_service.session.commit()
