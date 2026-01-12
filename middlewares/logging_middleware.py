"""Middleware для автоматического логирования всех действий пользователей"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


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
                self.message_logger.log_received(log_data)
                logger.debug(f"📥 Logged received: {log_data.get('action', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ Ошибка логирования входящего события: {e}", exc_info=True)

        # Вызываем следующий обработчик
        result = await handler(event, data)

        # Логируем исходящий ответ (если бот что-то отправил)
        # Примечание: aiogram автоматически отправляет ответы, поэтому
        # логирование исходящих сообщений лучше делать через хук на bot.send_message

        return result

    def _prepare_received_log(self, event: TelegramObject) -> Dict[str, Any]:
        """
        Подготовить данные для логирования входящего события

        Args:
            event: Message или CallbackQuery

        Returns:
            Словарь с данными для логирования
        """
        if isinstance(event, Message):
            return self._prepare_message_log(event)
        elif isinstance(event, CallbackQuery):
            return self._prepare_callback_log(event)
        return {}

    def _prepare_message_log(self, message: Message) -> Dict[str, Any]:
        """Подготовить данные логирования для обычного сообщения"""
        user = message.from_user

        log_data = {
            "user_id": user.id,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "action": "message",
            "text": message.text or "",
            "message_id": message.message_id,
            "chat_id": message.chat.id,
            "timestamp": message.date.isoformat() if message.date else "",
        }

        # Добавляем информацию о типе сообщения
        if message.text:
            if message.text.startswith('/'):
                log_data["action"] = f"command:{message.text.split()[0]}"
            else:
                log_data["action"] = "text_message"
        elif message.contact:
            log_data["action"] = "contact_shared"
            log_data["contact_phone"] = message.contact.phone_number
        elif message.location:
            log_data["action"] = "location_shared"
        elif message.photo:
            log_data["action"] = "photo_sent"
        elif message.document:
            log_data["action"] = "document_sent"

        return log_data

    def _prepare_callback_log(self, callback: CallbackQuery) -> Dict[str, Any]:
        """Подготовить данные логирования для callback-запроса"""
        user = callback.from_user

        log_data = {
            "user_id": user.id,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "action": f"callback:{callback.data}",
            "callback_data": callback.data or "",
            "message_id": callback.message.message_id if callback.message else 0,
            "chat_id": callback.message.chat.id if callback.message else 0,
            "timestamp": "",  # CallbackQuery не имеет date
        }

        return log_data


class BotResponseLoggingMiddleware:
    """
    Middleware для логирования исходящих сообщений от бота

    Этот middleware перехватывает вызовы bot.send_message и других методов отправки
    """

    def __init__(self, message_logger):
        """
        Args:
            message_logger: Экземпляр MessageLogger из services.message_logger
        """
        self.message_logger = message_logger
        self.logger = logging.getLogger(__name__)

    async def __call__(self, handler, event, data):
        """Базовый middleware для перехвата исходящих сообщений"""
        # Этот middleware работает на уровне бота, а не роутера
        # Его нужно регистрировать отдельно для перехвата исходящих сообщений
        result = await handler(event, data)

        # После выполнения обработчика логируем результат
        try:
            if result and hasattr(result, 'text'):
                # Это ответное сообщение от бота
                log_data = {
                    "bot_id": result.from_user.id if hasattr(result, 'from_user') else 0,
                    "chat_id": result.chat.id if hasattr(result, 'chat') else 0,
                    "text": result.text or "",
                    "message_id": result.message_id if hasattr(result, 'message_id') else 0,
                    "action": "bot_response",
                    "timestamp": result.date.isoformat() if hasattr(result, 'date') and result.date else "",
                }
                self.message_logger.log_sent(log_data)
                self.logger.debug(f"📤 Logged sent: bot_response")
        except Exception as e:
            self.logger.error(f"❌ Ошибка логирования исходящего сообщения: {e}", exc_info=True)

        return result
