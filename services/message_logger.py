import logging
import aiohttp
import asyncio
from typing import Dict, Any

class MessageLogger:
    def __init__(self, max_retries: int = 3, timeout: int = 5):
        self.received_endpoint = "https://app.pelagos.ru/tgbot-log/received/"
        self.sent_endpoint = "https://app.pelagos.ru/tgbot-log/sent/"
        self.max_retries = max_retries
        self.timeout = timeout
        self.api_key = "6tgbvcxdsfwerq31"
        self.logger = logging.getLogger("MessageLogger")

    async def _send_log(self, payload: Dict[str, Any], endpoint: str):
        """Отправка лога на сервер с повторными попытками"""
        headers = {"X-Key": self.api_key}

        for attempt in range(1, self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(endpoint, json=payload, headers=headers) as response:
                        if response.status == 200:
                            self.logger.debug(f"📤 Лог отправлен: {endpoint}")
                            return
                        else:
                            self.logger.warning(f"Ошибка {response.status} (попытка {attempt}/{self.max_retries})")
            except Exception as e:
                self.logger.error(f"Ошибка отправки лога (попытка {attempt}/{self.max_retries}): {e}")

            if attempt < self.max_retries:
                await asyncio.sleep(1)

        self.logger.error(f"❌ Не удалось отправить лог после {self.max_retries} попыток")

    def log_received(self, message_data: Dict[str, Any]):
        """Логирование входящего сообщения (неблокирующее)"""
        asyncio.create_task(self._send_log(message_data, self.received_endpoint))

    def log_sent(self, message_data: Dict[str, Any]):
        """Логирование исходящего сообщения (неблокирующее)"""
        asyncio.create_task(self._send_log(message_data, self.sent_endpoint))
