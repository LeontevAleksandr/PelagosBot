"""
Главный файл запуска телеграм-бота Pelagos Tours
"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN

# Импорт роутеров
from handlers import start, main_menu, profile, support, search, hotels, excursions, packages, transfers, order

# Инициализация Pelagos API и data_loader
from services.pelagos_api import PelagosAPI
from services.message_logger import MessageLogger
from utils.data_loader import set_data_loader, get_data_loader
from utils.preloader import init_preloader

# Импорт middleware
from middlewares import MessageLoggingMiddleware, setup_message_logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""

    # Проверка токена
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
        return

    # Инициализация Pelagos API
    api_key = os.getenv("PELAGOS_API_KEY")
    pelagos_api = PelagosAPI(api_key=api_key)

    # Инициализация DataLoader с API
    set_data_loader(pelagos_api)
    logger.info("✅ Pelagos API и DataLoader инициализированы")

    # Инициализация предзагрузчика отелей
    init_preloader(get_data_loader())
    logger.info("✅ Preloader инициализирован")

    # Инициализация MessageLogger для логирования действий пользователей
    message_logger = MessageLogger()
    logger.info("✅ MessageLogger инициализирован")

    # Инициализация бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Используем MemoryStorage для FSM
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация middleware для автоматического логирования
    dp.message.middleware(MessageLoggingMiddleware(message_logger))
    dp.callback_query.middleware(MessageLoggingMiddleware(message_logger))
    logger.info("✅ Logging middleware зарегистрирован")

    # Регистрация роутеров (порядок важен!)
    dp.include_router(start.router)
    dp.include_router(main_menu.router)
    dp.include_router(profile.router)  # Управление профилем пользователя
    dp.include_router(order.router)  # Управление заказом/корзиной
    dp.include_router(hotels.router)  # Флоу отелей
    dp.include_router(excursions.router)  # Флоу экскурсий
    dp.include_router(packages.router)  # Флоу пакетных туров
    dp.include_router(transfers.router)  # Флоу трансферов
    dp.include_router(support.router)
    dp.include_router(search.router)  # Должен быть последним для перехвата текста

    # Настраиваем логирование исходящих сообщений
    setup_message_logging(bot, message_logger)
    logger.info("✅ Логирование исходящих сообщений настроено")

    logger.info("✅ Бот запущен")

    try:
        # Удаляем вебхуки (если были)
        await bot.delete_webhook(drop_pending_updates=True)

        # Запуск polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await pelagos_api.close()
        logger.info("🛑 Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Бот остановлен пользователем")