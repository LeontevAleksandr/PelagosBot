"""Загрузчик островов с подсчетом экскурсий"""
import logging
import asyncio
from typing import List, Dict
from datetime import datetime, timedelta
from services.pelagos_api import PelagosAPI
from utils.cache_manager import CacheManager
from ..constants import CACHE_TTL_PRIVATE, PRIVATE_ISLANDS_MAP
from ..transformers import ServiceTransformer, DailyTransformer

logger = logging.getLogger(__name__)


class IslandFetcher:
    """Класс для загрузки островов с подсчетом экскурсий"""

    def __init__(self, api: PelagosAPI, cache: CacheManager):
        self.api = api
        self.cache = cache

    async def get_available_islands_with_count(self) -> List[Dict[str, any]]:
        """
        Загрузить все доступные острова с подсчётом индивидуальных + ежедневных экскурсий

        Returns:
            Список словарей: [{"location_id": int, "name": str, "count": int}, ...]
            Отсортирован по количеству экскурсий (от большего к меньшему)
        """
        # Проверяем кэш
        cache_key = "islands_with_count"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"✓ Кэш HIT: {len(cached)} островов с подсчётом")
            return cached

        try:
            logger.info("🔍 Загрузка всех экскурсий для подсчёта островов...")

            # Загружаем параллельно индивидуальные и ежедневные
            tomorrow = datetime.now() + timedelta(days=1)
            api_date = tomorrow.strftime("%d.%m.%Y")

            private_services, daily_services = await asyncio.gather(
                self.api.get_private_excursions(location_id=0, date=api_date),
                self.api.get_daily_excursions(location_id=0),
                return_exceptions=True
            )

            # Обрабатываем ошибки
            if isinstance(private_services, Exception):
                logger.error(f"Ошибка загрузки индивидуальных: {private_services}")
                private_services = []
            if isinstance(daily_services, Exception):
                logger.error(f"Ошибка загрузки ежедневных: {daily_services}")
                daily_services = []

            logger.info(f"📡 API: {len(private_services)} индивидуальных + {len(daily_services)} ежедневных")

            # Конвертируем все сервисы в словари
            all_excursions = []
            for service in private_services:
                exc_dict = ServiceTransformer.transform(service, "private")
                if exc_dict:
                    all_excursions.append(exc_dict)

            for service in daily_services:
                exc_dict = DailyTransformer.transform(service)
                if exc_dict:
                    all_excursions.append(exc_dict)

            # Кэшируем ВСЕ экскурсии
            self.cache.set("all_private_excursions", all_excursions, ttl=CACHE_TTL_PRIVATE)
            logger.info(f"💾 Закэшировано {len(all_excursions)} экскурсий")

            # Подсчитываем экскурсии по островам
            island_counts = {}
            for service in private_services + daily_services:
                location_id = service.get('location')

                # Фильтруем только наши острова (исключаем 6 и 12)
                if location_id in PRIVATE_ISLANDS_MAP:
                    if location_id not in island_counts:
                        island_counts[location_id] = 0
                    island_counts[location_id] += 1

            # Формируем результат
            islands = []
            for location_id, count in island_counts.items():
                islands.append({
                    "location_id": location_id,
                    "name": PRIVATE_ISLANDS_MAP[location_id],
                    "count": count
                })

            # Сортируем по количеству экскурсий (от большего к меньшему)
            islands.sort(key=lambda x: x['count'], reverse=True)

            logger.info(f"✅ Найдено {len(islands)} островов с экскурсиями:")
            for island in islands:
                logger.info(f"  • {island['name']}: {island['count']} экскурсий")

            # Кэшируем с увеличенным TTL
            self.cache.set(cache_key, islands, ttl=CACHE_TTL_PRIVATE)

            return islands

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки островов с подсчётом: {e}", exc_info=True)
            return []
