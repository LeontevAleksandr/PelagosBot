import logging
import aiohttp
import asyncio
import threading
from typing import Dict, Any

class MessageLogger:
    def __init__(self, max_retries: int = 3, timeout: int = 5):
        self.received_endpoint = "https://app.pelagos.ru/tgbot-log/received/"
        self.sent_endpoint = "https://app.pelagos.ru/tgbot-log/sent/"
        self.max_retries = max_retries
        self.timeout = timeout
        self.api_key = "6tgbvcxdsfwerq31"

        # Очередь задач для логирования
        self.task_queue = asyncio.Queue()

        # Настройка логирования
        self.logger = logging.getLogger("MessageLogger")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Запуск фонового потока для обработки задач
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

        # Запуск обработчика задач в event loop
        asyncio.run_coroutine_threadsafe(self._process_tasks(), self.loop)

    def _run_loop(self):
        self.logger.info("Запускаю event loop в отдельном потоке.")
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()  # Бесконечный цикл

    async def _process_tasks(self):
        self.logger.info("Обработчик задач запущен.")
        while True:
            self.logger.info("Ожидаю новую задачу...")
            task = await self.task_queue.get()
            self.logger.info(f"Обрабатываю задачу: {task}")
            payload, endpoint, headers = task
            await self._send_log(payload, endpoint, headers)
            self.task_queue.task_done()

    async def _send_log(self, payload: Dict[str, Any], endpoint: str, headers: Dict[str, str]):
        self.logger.info(f"Отправляю лог на {endpoint}: {payload}")
        for attempt in range(1, self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    self.logger.info(f"Создана сессия для отправки лога (попытка {attempt}).")
                    async with session.post(endpoint, json=payload, headers=headers) as response:
                        self.logger.info(f"Ответ сервера: статус {response.status}")
                        try:
                            response_data = await response.json()
                            self.logger.info(f"Тело ответа от сервера: {response_data}")
                        except Exception as e:
                            self.logger.warning(f"Не удалось прочитать тело ответа: {e}")
                        if response.status == 200:
                            self.logger.info(f"Лог отправлен: {payload}")
                            return
                        else:
                            self.logger.warning(f"Ошибка логирования (попытка {attempt}): {response.status}")
            except Exception as e:
                self.logger.error(f"Ошибка при отправке лога (попытка {attempt}): {e}")
            await asyncio.sleep(2)
        self.logger.error(f"Не удалось отправить лог после {self.max_retries} попыток.")

    def log_received(self, message_data: Dict[str, Any]):
        headers = {"X-Key": self.api_key}
        self.logger.info(f"Добавляю задачу в очередь (входящее): {message_data}")
        # Добавляем задачу в очередь потокобезопасно через event loop
        self.loop.call_soon_threadsafe(self.task_queue.put_nowait, (message_data, self.received_endpoint, headers))

    def log_sent(self, message_data: Dict[str, Any]):
        headers = {"X-Key": self.api_key}
        self.logger.info(f"Добавляю задачу в очередь (исходящее): {message_data}")
        self.loop.call_soon_threadsafe(self.task_queue.put_nowait, (message_data, self.sent_endpoint, headers))
