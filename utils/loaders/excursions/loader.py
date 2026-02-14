"""Главный класс-оркестратор для загрузки экскурсий"""
import logging
from typing import Optional, List, Dict
from services.pelagos_api import PelagosAPI
from utils.cache_manager import get_cache_manager
from .constants import CACHE_TTL_GROUP, CACHE_TTL_PRIVATE, CACHE_TTL_COMPANIONS
from .fetchers import PrivateFetcher, GroupFetcher, CompanionFetcher, IslandFetcher
from .transformers import BaseTransformer

logger = logging.getLogger(__name__)


class ExcursionsLoader:
    """
    Класс-оркестратор для работы с экскурсиями через Pelagos API

    Делегирует работу специализированным fetchers и transformers
    """

    def __init__(self, api: Optional[PelagosAPI] = None):
        self.api = api
        self.cache = get_cache_manager()

        # Инициализируем fetchers
        self.private_fetcher = PrivateFetcher(api, self.cache) if api else None
        self.group_fetcher = GroupFetcher(api, self.cache) if api else None
        self.companion_fetcher = CompanionFetcher(api, self.cache) if api else None
        self.island_fetcher = IslandFetcher(api, self.cache) if api else None

    # ========== Публичные методы для работы с островами ==========

    async def get_available_islands_with_count(self) -> List[Dict[str, any]]:
        """
        Загрузить все доступные острова с подсчётом индивидуальных + ежедневных экскурсий

        Returns:
            Список словарей: [{"location_id": int, "name": str, "count": int}, ...]
        """
        if not self.island_fetcher:
            logger.warning("⚠️ API не инициализирован")
            return []

        return await self.island_fetcher.get_available_islands_with_count()

    # ========== Публичные методы для работы с экскурсиями ==========

    async def get_excursions_by_filters(
        self,
        island: str = None,
        excursion_type: str = None,
        date: str = None
    ) -> list:
        """
        Получить экскурсии по фильтрам с кэшированием

        Args:
            island: код острова (cebu, bohol, boracay)
            excursion_type: тип экскурсии (group, private, companions)
            date: дата в формате YYYY-MM-DD

        Returns:
            список словарей с данными экскурсий
        """
        if not self.api:
            logger.warning("⚠️ API не инициализирован")
            return []

        # Индивидуальные экскурсии - отдельная логика
        if excursion_type == "private":
            return await self.private_fetcher.get_filtered(island=island)

        # Групповые экскурсии
        return await self.group_fetcher.get_by_filters(
            island=island,
            excursion_type=excursion_type,
            date=date
        )

    async def get_excursion_by_id(self, excursion_id: str) -> Optional[dict]:
        """
        Получить экскурсию по ID с кэшированием

        Автоматически определяет тип экскурсии и использует нужный fetcher

        Args:
            excursion_id: ID экскурсии

        Returns:
            Словарь с данными экскурсии или None
        """
        if not self.api:
            return None

        # Проверяем кэш
        cache_key = f"excursion:{excursion_id}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"✓ Кэш HIT: экскурсия {excursion_id}")
            return cached

        try:
            service_id = int(excursion_id)

            # Пробуем загрузить как групповую экскурсию (event)
            exc_dict = await self.group_fetcher.get_by_id(service_id)
            if exc_dict:
                self.cache.set(cache_key, exc_dict, ttl=CACHE_TTL_GROUP)
                return exc_dict

            # Пробуем как companion event
            exc_dict = await self.companion_fetcher.get_by_id(service_id)
            if exc_dict:
                self.cache.set(cache_key, exc_dict, ttl=CACHE_TTL_COMPANIONS)
                return exc_dict

            # Пробуем как индивидуальную экскурсию
            exc_dict = await self.private_fetcher.get_by_id(service_id)
            if exc_dict:
                self.cache.set(cache_key, exc_dict, ttl=CACHE_TTL_PRIVATE)
                return exc_dict

            logger.warning(f"⚠️ Экскурсия {excursion_id} не найдена")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки экскурсии {excursion_id}: {e}", exc_info=True)
            return None

    # ========== Методы для работы с попутчиками ==========

    async def get_companions_by_month(self, island: str, year: int, month: int) -> list:
        """
        Получить экскурсии с поиском попутчиков за месяц с кэшированием

        Args:
            island: код острова
            year: год
            month: месяц (1-12)

        Returns:
            список экскурсий с поиском попутчиков
        """
        if not self.companion_fetcher:
            return []

        return await self.companion_fetcher.get_by_month(island, year, month)

    async def get_companion_event_by_id(self, event_id: str) -> Optional[dict]:
        """
        Получить companion event по event_id с полными данными (slst)

        Args:
            event_id: ID события

        Returns:
            словарь с данными экскурсии или None
        """
        if not self.companion_fetcher:
            return None

        try:
            event_id_int = int(event_id)
            return await self.companion_fetcher.get_by_id(event_id_int)
        except ValueError:
            logger.error(f"❌ Неверный формат event_id: {event_id}")
            return None

    # ========== Методы для предзагрузки ==========

    async def preload_private_excursions(self, island: str = None):
        """
        Предзагрузка индивидуальных экскурсий в фоне

        Использование: вызывать при выборе острова/типа экскурсии

        Args:
            island: код/ID острова или None для всех
        """
        if not self.private_fetcher:
            return

        await self.private_fetcher.preload(island)

    # ========== Вспомогательные методы (для обратной совместимости) ==========

    def _get_island_info(self, location_id: int) -> tuple:
        """Получить код острова и название по location ID (deprecated)"""
        return BaseTransformer.get_island_info(location_id)

    def _clean_html(self, html: str) -> str:
        """Очистить HTML от тегов (deprecated)"""
        return BaseTransformer.clean_html(html)

    def _build_photo_url(self, pic: dict) -> Optional[str]:
        """Построить URL фото (deprecated)"""
        return BaseTransformer.build_photo_url(pic)

    def _extract_price_list(self, rlst: list) -> Dict[int, float]:
        """Извлечь список цен (deprecated)"""
        return BaseTransformer.extract_price_list(rlst)
