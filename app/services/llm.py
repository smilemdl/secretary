from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from openai import OpenAI

from app.config import Settings
from app.domain import CommandType, ParsedCommand
from app.time_utils import to_utc_naive


@dataclass
class LLMInterpreter:
    settings: Settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.llm_api_key and self.settings.llm_model)

    def parse(self, text: str, now_local: datetime) -> ParsedCommand | None:
        if not self.enabled:
            return None

        client_kwargs = {"api_key": self.settings.llm_api_key}
        if self.settings.llm_base_url:
            client_kwargs["base_url"] = self.settings.llm_base_url
        client = OpenAI(**client_kwargs)

        request_kwargs = {
            "model": self.settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a command parser for a personal scheduler web app. "
                        "Return json only. "
                        "Allowed keys: kind, title, scheduled_at, question. "
                        "kind must be one of CREATE_TASK, LIST_TODAY, LIST_PENDING, COMPLETE_LATEST, "
                        "CANCEL_LATEST, SNOOZE_LATEST, RESCHEDULE_LATEST, CLARIFY, UNKNOWN. "
                        "Use CLARIFY if time is ambiguous. scheduled_at must be ISO 8601 if present. "
                        "Interpret Chinese time expressions in Asia/Shanghai local time. "
                        "For example, 下午三点 means 15:00 local time."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Current local time: {now_local.strftime('%Y-%m-%d %H:%M:%S')}\\n"
                        f"User message: {text}"
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        if self.settings.llm_base_url and "dashscope.aliyuncs.com" in self.settings.llm_base_url:
            request_kwargs["extra_body"] = {"enable_thinking": self.settings.llm_enable_thinking}

        response = client.chat.completions.create(**request_kwargs)
        raw = response.choices[0].message.content or ""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None

        kind = data.get("kind", CommandType.UNKNOWN.value)
        if kind not in {item.value for item in CommandType}:
            kind = CommandType.UNKNOWN.value

        scheduled_at = None
        raw_scheduled_at = data.get("scheduled_at")
        if isinstance(raw_scheduled_at, str) and raw_scheduled_at:
            try:
                parsed_dt = datetime.fromisoformat(raw_scheduled_at)
                if parsed_dt.tzinfo is None:
                    scheduled_at = to_utc_naive(parsed_dt, self.settings.default_timezone)
                else:
                    scheduled_at = parsed_dt.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)
            except ValueError:
                scheduled_at = None

        return ParsedCommand(
            kind=CommandType(kind),
            raw_text=text,
            title=data.get("title"),
            scheduled_at=scheduled_at,
            question=data.get("question"),
        )
