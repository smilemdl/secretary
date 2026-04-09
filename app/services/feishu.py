from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

import requests

from app.config import Settings


logger = logging.getLogger(__name__)


@dataclass
class IncomingMessage:
    event_id: str
    message_id: str
    chat_id: str
    open_id: str
    text: str
    mentioned: bool


class FeishuClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cached_token: str | None = None
        self._token_expire_at: float = 0

    @property
    def enabled(self) -> bool:
        return bool(self.settings.feishu_app_id and self.settings.feishu_app_secret)

    def send_text(self, chat_id: str, text: str) -> bool:
        if not self.enabled:
            logger.warning("Feishu is not configured, skip sending message to %s: %s", chat_id, text)
            return False

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self._get_tenant_access_token()}",
            "Content-Type": "application/json",
        }
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        response = requests.post(url, headers=headers, params={"receive_id_type": "chat_id"}, json=payload, timeout=10)
        response.raise_for_status()
        body = response.json()
        if body.get("code") != 0:
            raise RuntimeError(f"Feishu send message failed: {body}")
        return True

    def _get_tenant_access_token(self) -> str:
        if self._cached_token and time.time() < self._token_expire_at:
            return self._cached_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.settings.feishu_app_id, "app_secret": self.settings.feishu_app_secret}
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        body = response.json()
        if body.get("code") != 0:
            raise RuntimeError(f"Feishu token fetch failed: {body}")

        expire = body.get("expire", 7200)
        self._cached_token = body["tenant_access_token"]
        self._token_expire_at = time.time() + expire - 60
        return self._cached_token


def parse_event(payload: dict[str, object]) -> IncomingMessage | None:
    header = payload.get("header")
    event = payload.get("event")
    if not isinstance(header, dict) or not isinstance(event, dict):
        return None
    if header.get("event_type") != "im.message.receive_v1":
        return None

    message = event.get("message", {})
    sender = event.get("sender", {})
    if not isinstance(message, dict) or not isinstance(sender, dict):
        return None

    if message.get("message_type") != "text":
        return None

    content = message.get("content", "{}")
    try:
        content_body = json.loads(content)
    except json.JSONDecodeError:
        content_body = {"text": str(content)}

    raw_text = str(content_body.get("text", "")).strip()
    sender_id = sender.get("sender_id") or {}
    return IncomingMessage(
        event_id=str(header.get("event_id", "")),
        message_id=str(message.get("message_id", "")),
        chat_id=str(message.get("chat_id", "")),
        open_id=str(sender_id.get("open_id", "")),
        text=raw_text,
        mentioned="@_user_" in raw_text,
    )