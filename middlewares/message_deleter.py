"""Middleware для автоматического удаления временных сообщений"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import asyncio


class MessageDeleterMiddleware(BaseMiddleware):
    """
    Middleware для удаления временных сообщений пользователя.
    Важные информационные блоки остаются в переписке.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем флаги из data (будут устанавливаться в хендлерах)
        delete_user_message = data.get("delete_user_message", True)
        delete_bot_message = data.get("delete_bot_message", False)
        keep_info_block = data.get("keep_info_block", False)
        
        # Сохраняем ID сообщений для последующего удаления
        messages_to_delete = []
        
        # Если это сообщение от пользователя и нужно удалить
        if isinstance(event, Message) and delete_user_message:
            messages_to_delete.append({
                "chat_id": event.chat.id,
                "message_id": event.message_id
            })
        
        # Вызываем обработчик
        result = await handler(event, data)
        
        # Если хендлер вернул сообщение для удаления
        if isinstance(result, Message) and delete_bot_message and not keep_info_block:
            messages_to_delete.append({
                "chat_id": result.chat.id,
                "message_id": result.message_id
            })
        
        # Удаляем сообщения с небольшой задержкой
        if messages_to_delete:
            asyncio.create_task(self._delete_messages_delayed(event, messages_to_delete))
        
        return result
    
    async def _delete_messages_delayed(
        self, 
        event: Message | CallbackQuery, 
        messages: list[dict],
        delay: float = 0.5
    ):
        """Удаляет сообщения с задержкой"""
        await asyncio.sleep(delay)
        
        bot = event.bot
        for msg in messages:
            try:
                await bot.delete_message(
                    chat_id=msg["chat_id"],
                    message_id=msg["message_id"]
                )
            except Exception:
                # Игнорируем ошибки (сообщение уже удалено или недоступно)
                pass