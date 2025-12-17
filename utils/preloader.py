"""Фоновая предзагрузка отелей для ускорения навигации"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class HotelPreloader:
    """Умная предзагрузка следующих отелей в фоне"""

    def __init__(self, data_loader):
        self.data_loader = data_loader
        self._tasks = {}  # {cache_key: Task}

    def _make_key(self, island: str, stars: Optional[int], page: int) -> str:
        """Генерация ключа для задачи"""
        return f"{island}:{stars or 'all'}:{page}"

    async def _load_page(self, island: str, stars: Optional[int], page: int,
                         check_in: Optional[str], check_out: Optional[str]):
        """Фоновая загрузка страницы"""
        try:
            logger.debug(f"🔄 Предзагрузка: остров={island}, звезды={stars}, страница={page}")
            await self.data_loader.get_hotels_by_filters(
                island=island,
                stars=stars,
                page=page,
                per_page=5,
                check_in=check_in,
                check_out=check_out
            )
            logger.debug(f"✅ Предзагрузка завершена: страница {page}")
        except Exception as e:
            logger.error(f"❌ Ошибка предзагрузки страницы {page}: {e}")

    def preload_next(self, island: str, stars: Optional[int], current_page: int,
                     check_in: Optional[str], check_out: Optional[str]):
        """
        Запустить предзагрузку следующей страницы

        Args:
            island: код острова
            stars: количество звезд (или None)
            current_page: текущая страница (1-based)
            check_in: дата заезда
            check_out: дата выезда
        """
        next_page = current_page  # Конвертируем в 0-based для API
        key = self._make_key(island, stars, next_page)

        # Если уже загружается - пропускаем
        if key in self._tasks and not self._tasks[key].done():
            return

        # Запускаем фоновую загрузку
        task = asyncio.create_task(
            self._load_page(island, stars, next_page, check_in, check_out)
        )
        self._tasks[key] = task

        # Очистка старых завершенных задач
        self._cleanup_tasks()

    def _cleanup_tasks(self):
        """Удаление завершенных задач"""
        self._tasks = {k: v for k, v in self._tasks.items() if not v.done()}


# Глобальный экземпляр
_preloader_instance = None


def get_preloader():
    """Получить экземпляр предзагрузчика"""
    return _preloader_instance


def init_preloader(data_loader):
    """Инициализировать предзагрузчик"""
    global _preloader_instance
    _preloader_instance = HotelPreloader(data_loader)
