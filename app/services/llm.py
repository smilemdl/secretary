from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI

from app.config import Settings
from app.domain import CommandType, ParsedCommand


@dataclass
class LLMInterpreter:
    settings: Settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.openai_api_key)

    def parse(self, text: str, now_local: datetime) -> ParsedCommand | None:
        if not self.enabled:
            return None

        client = OpenAI(api_key=self.settings.openai_api_key)
        prompt = (
            "You are a command parser for a Feishu scheduler bot. "
            "Return JSON only with kind/title/scheduled_at/question. "
            "kind must be one of CREATE_TASK, LIST_TODAY, LIST_PENDING, COMPLETE_LATEST, "
            "CANCEL_LATEST, SNOOZE_LATEST, RESCHEDULE_LATEST, CLARIFY, UNKNOWN. "
            "If time is ambiguous, return CLARIFY. "
            f"Current local time: {now_local.strftime('%Y-%m-%d %H:%M:%S')}. "
            f"User message: {text}"
        )
        response = client.responses.create(model=self.settings.openai_model, input=prompt)
        raw = response.output_text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None

        kind = data.get("kind", CommandType.UNKNOWN.value)
        if kind not in {item.value for item in CommandType}:
            kind = CommandType.UNKNOWN.value

        scheduled_at = None
        raw_scheduled_at = data.get("scheduled_at")
        if isinstance(raw_scheduled_at, str) and raw_scheduled_at:
            try:
                scheduled_at = datetime.fromisoformat(raw_scheduled_at)
            except ValueError:
                scheduled_at = None

        return ParsedCommand(
            kind=CommandType(kind),
            raw_text=text,
            title=data.get("title"),
            scheduled_at=scheduled_at,
            question=data.get("question"),
        )