from __future__ import annotations

import logging
import os
from typing import Any

import requests


LOGGER = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None, timeout: int = 20):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_item(self, item: dict[str, Any]) -> bool:
        if not self.is_configured():
            return False
        text = self.format_message(item)
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "disable_web_page_preview": False},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as error:
            LOGGER.error("Telegram notification failed: %s", error)
            return False

    @staticmethod
    def format_message(item: dict[str, Any]) -> str:
        lines = [
            "Новый релевантный земельный лот",
            f"Станция: {item.get('station_match') or 'не определена'}",
            f"Площадь: {item.get('area_m2') or 'не указана'} м²",
            f"Тип: {item.get('purpose') or '-'} / {item.get('contract_type') or '-'}",
            f"Дедлайн: {item.get('application_deadline') or '-'}",
            f"Название: {item.get('title')}",
        ]
        if item.get("url"):
            lines.append(str(item["url"]))
        return "\n".join(lines)
