"""Загрузчик индивидуальных экскурсий"""
import logging
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from services.pelagos_api import PelagosAPI
from utils.cache_manager import CacheManager
from ..constants import CACHE_TTL_PRIVATE, CACHE_TTL_DAILY, LOCATION_MAP, PRIVATE_ISLANDS_MAP
from ..transformers import ServiceTransformer, DailyTransformer

logger = logging.getLogger(__name__)


class PrivateFetcher:
    """Класс для загрузки индивидуальных экскурсий"""

    def __init__(self, api: PelagosAPI, cache: CacheManager):
        self.api = api
        self.cache = cache
        self._preload_tasks = {}  # Храним фоновые задачи предзагрузки

    async def get_filtered(self, island: str = None) -> List[dict]:
        """
        Получить индивидуальные + ежедневные экскурсии с кэшированием

        Args:
            island: location_id в виде строки (например, "9" для Себу) или None для всех

        Returns:
            Список словарей с данными экскурсий
        """
        try:
            # Если остров указан - делаем прямой API запрос с фильтром
            if island:
                try:
                    location_id = int(island)

                    # Проверяем кэш для конкретного острова
                    cache_key = f"private_excursions_island_{location_id}"
                    cached = self.cache.get(cache_key)
                    if cached:
                        logger.info(f"✓ Кэш HIT: {len(cached)} экскурсий для острова {PRIVATE_ISLANDS_MAP.get(location_id, location_id)}")
                        return cached

                    logger.info(f"🔍 Загрузка экскурсий для location_id={location_id} ({PRIVATE_ISLANDS_MAP.get(location_id, location_id)})")

                    # Загружаем параллельно индивидуальные и ежедневные
                    tomorrow = datetime.now() + timedelta(days=1)
                    api_date = tomorrow.strftime("%d.%m.%Y")

                    private_services, daily_services = await asyncio.gather(
                        self.api.get_private_excursions(location_id=location_id, date=api_date),
                        self.api.get_daily_excursions(location_id=location_id),
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

                    # Конвертируем services в словари
                    excursions = []
                    for service in private_services:
                        exc_dict = ServiceTransformer.transform(service, "private")
                        if exc_dict:
                            excursions.append(exc_dict)

                    for service in daily_services:
                        exc_dict = DailyTransformer.transform(service)
                        if exc_dict:
                            excursions.append(exc_dict)

                    # Кэшируем результат для этого острова
                    self.cache.set(cache_key, excursions, ttl=CACHE_TTL_PRIVATE)

                    logger.info(f"✅ Возвращаем {len(excursions)} экскурсий для острова {PRIVATE_ISLANDS_MAP.get(location_id, location_id)}")
                    return excursions

                except ValueError:
                    # Если передан старый формат (код острова типа "cebu")
                    location_id = LOCATION_MAP.get(island.lower(), 0)
                    logger.info(f"🔍 Загрузка индивидуальных экскурсий (старый формат): {island} (id={location_id})")

                    tomorrow = datetime.now() + timedelta(days=1)
                    api_date = tomorrow.strftime("%d.%m.%Y")

                    services = await self.api.get_private_excursions(
                        location_id=location_id,
                        date=api_date
                    )

                    excursions = [
                        exc for exc in (ServiceTransformer.transform(s, "private") for s in services)
                        if exc and exc.get('island') == island.lower()
                    ]

                    logger.info(f"✅ Возвращаем {len(excursions)} индивидуальных экскурсий")
                    return excursions
            else:
                # Если остров не указан - загружаем все экскурсии через общий кэш
                all_excursions = self.cache.get("all_private_excursions")

                if not all_excursions:
                    # Если нет в кэше - нужно загрузить через island_fetcher
                    logger.info("🔄 Кэш пуст, нужно загрузить все экскурсии...")
                    return []

                # Возвращаем все экскурсии
                logger.info(f"✅ Возвращаем все {len(all_excursions)} индивидуальных экскурсий")
                return all_excursions

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки индивидуальных экскурсий: {e}", exc_info=True)
            return []

    async def get_daily_filtered(self, island: str = None) -> List[dict]:
        """
        Получить ежедневные экскурсии с кэшированием

        Args:
            island: location_id в виде строки или None для всех

        Returns:
            список словарей с ежедневными экскурсиями
        """
        try:
            # Определяем location_id
            location_id = 0
            if island:
                try:
                    location_id = int(island)
                except ValueError:
                    location_id = LOCATION_MAP.get(island.lower(), 0)

            # Проверяем кэш
            cache_key = f"daily_excursions_island_{location_id}"
            cached = self.cache.get(cache_key)
            if cached:
                logger.info(f"✓ Кэш HIT: {len(cached)} ежедневных экскурсий")
                return cached

            logger.info(f"🔍 Загрузка ежедневных экскурсий для location_id={location_id}")

            # Загружаем ежедневные экскурсии
            services = await self.api.get_daily_excursions(location_id=location_id)

            logger.info(f"📡 API вернул {len(services)} ежедневных экскурсий")

            # Конвертируем в словари
            excursions = []
            for service in services:
                exc_dict = DailyTransformer.transform(service)
                if exc_dict:
                    excursions.append(exc_dict)

            # Кэшируем
            self.cache.set(cache_key, excursions, ttl=CACHE_TTL_DAILY)

            logger.info(f"✅ Возвращаем {len(excursions)} ежедневных экскурсий")
            return excursions

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки ежедневных экскурсий: {e}", exc_info=True)
            return []

    async def preload(self, island: str = None):
        """
        Предзагрузка индивидуальных экскурсий в фоне

        Использование: вызывать при выборе острова/типа экскурсии

        Args:
            island: код/ID острова или None для всех
        """
        cache_key = f"excursions_private:{island or 'all'}"

        # Если уже есть в кэше - не грузим
        if self.cache.get(cache_key):
            return

        # Если уже грузим - не дублируем
        if cache_key in self._preload_tasks:
            return

        # Запускаем фоновую задачу
        logger.info(f"🚀 Запуск предзагрузки индивидуальных экскурсий для {island or 'всех островов'}")
        task = asyncio.create_task(self.get_filtered(island))
        self._preload_tasks[cache_key] = task

        # Очищаем задачу после выполнения
        def cleanup(_):
            self._preload_tasks.pop(cache_key, None)
        task.add_done_callback(cleanup)

    async def get_by_id(self, excursion_id: int) -> Optional[dict]:
        """
        Получить индивидуальную экскурсию по ID

        Сначала ищем в кэшах островов, потом делаем API запрос

        Args:
            excursion_id: ID экскурсии

        Returns:
            Словарь с данными экскурсии или None
        """
        try:
            # Проверяем кэши для конкретных островов
            for location_id in PRIVATE_ISLANDS_MAP.keys():
                island_cache_key = f"private_excursions_island_{location_id}"
                island_cached = self.cache.get(island_cache_key)
                if island_cached:
                    for exc in island_cached:
                        if exc.get('id') == str(excursion_id) or exc.get('service_id') == str(excursion_id):
                            logger.info(f"✓ Найдена индивидуальная экскурсия {excursion_id} в кэше острова")
                            return exc

            # Проверяем общий кэш
            all_private_cache = self.cache.get("all_private_excursions")
            if all_private_cache:
                for exc in all_private_cache:
                    if exc.get('id') == str(excursion_id) or exc.get('service_id') == str(excursion_id):
                        logger.info(f"✓ Найдена индивидуальная экскурсия {excursion_id} в общем кэше")
                        return exc

            # Если не нашли в кэше - загружаем все индивидуальные экскурсии
            tomorrow = datetime.now() + timedelta(days=1)
            api_date = tomorrow.strftime("%d.%m.%Y")

            logger.info(f"⚠️ Экскурсия {excursion_id} не найдена в кэше, загружаем все индивидуальные экскурсии...")
            services = await self.api.get_private_excursions(location_id=0, date=api_date)

            for service_data in services:
                if service_data.get('id') == excursion_id:
                    exc_dict = ServiceTransformer.transform(service_data, "private")
                    logger.info(f"✓ Найдена индивидуальная экскурсия {excursion_id}")
                    return exc_dict

            logger.warning(f"⚠️ Экскурсия {excursion_id} не найдена")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки индивидуальной экскурсии {excursion_id}: {e}", exc_info=True)
            return None
