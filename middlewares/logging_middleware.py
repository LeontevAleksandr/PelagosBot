"""Middleware для автоматического логирования всех действий пользователей"""
import logging
import asyncio
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)

# Глобальное хранилище фоновых задач для логирования
background_logging_tasks = set()


class MessageLoggingMiddleware(BaseMiddleware):
    """Middleware для логирования входящих сообщений и callback-запросов"""

    def __init__(self, message_logger):
        """
        Args:
            message_logger: Экземпляр MessageLogger из services.message_logger
        """
        self.message_logger = message_logger
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """
        Обрабатывает входящее событие, логирует его и результат

        Args:
            handler: Следующий обработчик в цепочке
            event: Событие (Message или CallbackQuery)
            data: Дополнительные данные
        """
        # Логируем входящее сообщение/действие
        try:
            log_data = self._prepare_received_log(event)
            if log_data:
                task = asyncio.create_task(
                    self.message_logger._send_log(log_data, self.message_logger.received_endpoint)
                )
                background_logging_tasks.add(task)
                task.add_done_callback(background_logging_tasks.discard)
        except Exception as e:
            logger.error(f"Ошибка логирования входящего события: {e}")

        # Вызываем следующий обработчик
        result = await handler(event, data)

        return result

    def _prepare_received_log(self, event: TelegramObject) -> Dict[str, Any]:
        """Подготовить данные для логирования входящего события"""
        if isinstance(event, Message):
            return self._prepare_message_log(event)
        elif isinstance(event, CallbackQuery):
            return self._prepare_callback_log(event)
        return {}

    def _prepare_message_log(self, message: Message) -> Dict[str, Any]:
        """Подготовить данные логирования для обычного сообщения"""
        user = message.from_user
        return {
            "message": {
                "text": message.text or "",
                "chat_id": message.chat.id,
                "from_user": user.username or ""
            }
        }

    def _prepare_callback_log(self, callback: CallbackQuery) -> Dict[str, Any]:
        """Подготовить данные логирования для callback-запроса"""
        user = callback.from_user
        return {
            "callback_query": {
                "id": str(callback.id),
                "data": callback.data or "",
                "chat_id": callback.message.chat.id if callback.message else 0,
                "from_user": user.username or ""
            }
        }


def setup_message_logging(bot, message_logger):
    """
    Настроить логирование исходящих сообщений через monkey patching

    Args:
        bot: Экземпляр Bot
        message_logger: Экземпляр MessageLogger
    """
    original_answer = Message.answer
    original_edit_text = Message.edit_text

    async def logged_answer(self, text, **kwargs):
        """Обёртка для message.answer()"""
        result = await original_answer(self, text, **kwargs)
        
        log_data = {"message": {"text": text, "chat_id": self.chat.id}}
        task = asyncio.create_task(
            message_logger._send_log(log_data, message_logger.sent_endpoint)
        )
        background_logging_tasks.add(task)
        task.add_done_callback(background_logging_tasks.discard)
        
        return result

    async def logged_edit_text(self, text, **kwargs):
        """Обёртка для message.edit_text()"""
        result = await original_edit_text(self, text, **kwargs)
        
        log_data = {"message": {"text": text, "chat_id": self.chat.id}}
        task = asyncio.create_task(
            message_logger._send_log(log_data, message_logger.sent_endpoint)
        )
        background_logging_tasks.add(task)
        task.add_done_callback(background_logging_tasks.discard)
        
        return result

    Message.answer = logged_answer
    Message.edit_text = logged_edit_text