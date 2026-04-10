from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    database_url: str
    default_timezone: str
    default_owner_id: str
    default_context_id: str
    openai_api_key: str
    openai_model: str
    reminder_scan_interval_seconds: int
    web_poll_interval_seconds: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Secretary Web MVP"),
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./secretary.db"),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "Asia/Shanghai"),
        default_owner_id=os.getenv("DEFAULT_OWNER_ID", "local-user"),
        default_context_id=os.getenv("DEFAULT_CONTEXT_ID", "web"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        reminder_scan_interval_seconds=_get_int("REMINDER_SCAN_INTERVAL_SECONDS", 15),
        web_poll_interval_seconds=_get_int("WEB_POLL_INTERVAL_SECONDS", 15),
    )
