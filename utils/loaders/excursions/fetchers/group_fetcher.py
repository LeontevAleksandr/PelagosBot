"""Загрузчик групповых экскурсий"""
import logging
from typing import List, Optional
from services.pelagos_api import PelagosAPI
from utils.cache_manager import CacheManager
from ..constants import CACHE_TTL_GROUP
from ..transformers import EventTransformer

logger = logging.getLogger(__name__)


class GroupFetcher:
    """Класс для загрузки групповых экскурсий"""

    def __init__(self, api: PelagosAPI, cache: CacheManager):
        self.api = api
        self.cache = cache

    async def get_by_filters(
        self,
        island: str = None,
        excursion_type: str = None,
        date: str = None
    ) -> List[dict]:
        """
        Получить групповые экскурсии по фильтрам с кэшированием

        Args:
            island: код острова (cebu, bohol, boracay)
            excursion_type: тип экскурсии
            date: дата в формате YYYY-MM-DD

        Returns:
            список словарей с данными экскурсий
        """
        # Проверяем кэш
        cache_key = f"excursions:{island or 'all'}:{excursion_type or 'all'}:{date or 'all'}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"✓ Кэш HIT: {len(cached)} экскурсий")
            return cached

        try:
            logger.info(f"🔍 Загрузка: island={island}, type={excursion_type}, date={date}")

            # Получаем события из API
            events = await self.api.get_excursions_by_location_and_date(
                location_code=island,
                date=date
            )

            logger.info(f"📡 API вернул {len(events)} событий")

            # Конвертируем в dict
            excursions = []
            for event in events:
                exc_dict = EventTransformer.transform(event, excursion_type or "group")
                if exc_dict:
                    excursions.append(exc_dict)

            # Кэшируем
            self.cache.set(cache_key, excursions, ttl=CACHE_TTL_GROUP)

            logger.info(f"✅ Возвращаем {len(excursions)} экскурсий")
            return excursions

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки экскурсий: {e}", exc_info=True)
            return []

    async def get_by_id(self, excursion_id: int) -> Optional[dict]:
        """
        Получить групповую экскурсию по ID

        Args:
            excursion_id: ID экскурсии

        Returns:
            Словарь с данными экскурсии или None
        """
        try:
            event = await self.api.get_excursion_event_details(excursion_id)
            if event:
                return EventTransformer.transform(event)
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки групповой экскурсии {excursion_id}: {e}", exc_info=True)
            return None
