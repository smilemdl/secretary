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
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str
    feishu_bot_name: str
    openai_api_key: str
    openai_model: str
    reminder_scan_interval_seconds: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Secretary MVP"),
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./secretary.db"),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "Asia/Shanghai"),
        feishu_app_id=os.getenv("FEISHU_APP_ID", ""),
        feishu_app_secret=os.getenv("FEISHU_APP_SECRET", ""),
        feishu_verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", ""),
        feishu_bot_name=os.getenv("FEISHU_BOT_NAME", "助手"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        reminder_scan_interval_seconds=_get_int("REMINDER_SCAN_INTERVAL_SECONDS", 60),
    )