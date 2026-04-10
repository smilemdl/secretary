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


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    database_url: str
    default_timezone: str
    default_owner_id: str
    default_context_id: str
    llm_api_key: str
    llm_model: str
    llm_base_url: str
    llm_enable_thinking: bool
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
        llm_api_key=os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        llm_model=os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
        llm_base_url=os.getenv("LLM_BASE_URL", ""),
        llm_enable_thinking=_get_bool("LLM_ENABLE_THINKING", False),
        reminder_scan_interval_seconds=_get_int("REMINDER_SCAN_INTERVAL_SECONDS", 15),
        web_poll_interval_seconds=_get_int("WEB_POLL_INTERVAL_SECONDS", 15),
    )
