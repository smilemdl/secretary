from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal, get_session, init_db
from app.models import MessageDedup
from app.services.command_handler import CommandHandler
from app.services.feishu import FeishuClient, parse_event
from app.services.reminder_service import ReminderService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_scheduler(settings: Settings) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=settings.default_timezone)
    reminder_service = ReminderService(SessionLocal, FeishuClient(settings), settings)
    scheduler.add_job(
        reminder_service.process_due_tasks,
        "interval",
        seconds=settings.reminder_scan_interval_seconds,
        id="scan_due_tasks",
        replace_existing=True,
    )
    scheduler.add_job(
        reminder_service.send_evening_summary,
        CronTrigger(hour=20, minute=30, timezone=settings.default_timezone),
        id="evening_summary",
        replace_existing=True,
    )
    scheduler.add_job(
        reminder_service.send_overdue_summary,
        CronTrigger(hour=9, minute=0, timezone=settings.default_timezone),
        id="overdue_summary",
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


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/feishu/events")
def feishu_events(
    payload: dict,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    challenge = payload.get("challenge")
    if challenge:
        return {"challenge": challenge}

    verification_token = payload.get("token")
    if settings.feishu_verification_token and verification_token != settings.feishu_verification_token:
        raise HTTPException(status_code=403, detail="invalid verification token")

    incoming = parse_event(payload)
    if incoming is None or not incoming.mentioned:
        return {"code": 0}

    if not incoming.event_id or not incoming.message_id:
        return {"code": 0}

    existing = session.scalar(select(MessageDedup).where(MessageDedup.event_id == incoming.event_id))
    if existing is not None:
        return {"code": 0}

    handler = CommandHandler(session, settings)
    result = handler.handle_message(
        owner_open_id=incoming.open_id,
        chat_id=incoming.chat_id,
        message_id=incoming.message_id,
        text=incoming.text,
    )

    dedup = MessageDedup(
        event_id=incoming.event_id,
        message_id=incoming.message_id,
        result_hash=hashlib.sha256(result.reply_text.encode("utf-8")).hexdigest(),
    )
    session.add(dedup)
    session.commit()

    try:
        FeishuClient(settings).send_text(incoming.chat_id, result.reply_text)
    except Exception as exc:
        logger.exception("Failed to send reply to Feishu: %s", exc)

    return {"code": 0}