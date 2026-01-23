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
                # Создаём фоновую задачу для логирования
                task = asyncio.create_task(
                    self.message_logger._send_log(log_data, self.message_logger.received_endpoint)
                )
                background_logging_tasks.add(task)
                task.add_done_callback(background_logging_tasks.discard)
                
                logger.debug(f"📥 Logged received: {log_data.get('message', {}).get('text', 'callback')}")
        except Exception as e:
            logger.error(f"❌ Ошибка логирования входящего события: {e}", exc_info=True)

        # Вызываем следующий обработчик
        result = await handler(event, data)

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
        """Подготовить данные логирования для обычного сообщения в формате старого бота"""
        user = message.from_user

        # Формат для старого бота
        log_data = {
            "message": {
                "text": message.text or "",
                "chat_id": message.chat.id,
                "from_user": user.username or ""
            }
        }

        return log_data

    def _prepare_callback_log(self, callback: CallbackQuery) -> Dict[str, Any]:
        """Подготовить данные логирования для callback-запроса в формате старого бота"""
        user = callback.from_user

        # Формат для старого бота
        log_data = {
            "callback_query": {
                "id": str(callback.id),
                "data": callback.data or "",
                "chat_id": callback.message.chat.id if callback.message else 0,
                "from_user": user.username or ""
            }
        }

        return log_data


def setup_message_logging(bot, message_logger):
    """
    Настроить логирование исходящих сообщений через monkey patching

    Args:
        bot: Экземпляр Bot
        message_logger: Экземпляр MessageLogger
    """
    logger_instance = logging.getLogger(__name__)

    # Сохраняем оригинальные методы
    original_send_message = bot.send_message
    original_edit_message_text = bot.edit_message_text

    async def logged_send_message(chat_id, text, **kwargs):
        """Обёртка для send_message с логированием"""
        try:
            result = await original_send_message(chat_id, text, **kwargs)

            # Логируем исходящее сообщение в формате старого бота
            log_data = {
                "message": {
                    "text": text,
                    "chat_id": chat_id
                }
            }
            
            # Создаём фоновую задачу для логирования (неблокирующее)
            task = asyncio.create_task(
                message_logger._send_log(log_data, message_logger.sent_endpoint)
            )
            background_logging_tasks.add(task)
            task.add_done_callback(background_logging_tasks.discard)
            
            logger_instance.debug(f"📤 Logged sent message to chat {chat_id}")

            return result
        except Exception as e:
            logger_instance.error(f"❌ Ошибка при отправке/логировании сообщения: {e}", exc_info=True)
            raise

    async def logged_edit_message_text(text, chat_id=None, message_id=None, inline_message_id=None, **kwargs):
        """Обёртка для edit_message_text с логированием"""
        try:
            result = await original_edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                inline_message_id=inline_message_id,
                **kwargs
            )

            # Логируем изменённое сообщение
            if chat_id:
                log_data = {
                    "message": {
                        "text": text,
                        "chat_id": chat_id
                    }
                }
                
                # Создаём фоновую задачу для логирования (неблокирующее)
                task = asyncio.create_task(
                    message_logger._send_log(log_data, message_logger.sent_endpoint)
                )
                background_logging_tasks.add(task)
                task.add_done_callback(background_logging_tasks.discard)
                
                logger_instance.debug(f"📤 Logged edited message in chat {chat_id}")

            return result
        except Exception as e:
            logger_instance.error(f"❌ Ошибка при редактировании/логировании сообщения: {e}", exc_info=True)
            raise

    # Заменяем методы бота на обёртки
    bot.send_message = logged_send_message
    bot.edit_message_text = logged_edit_message_text