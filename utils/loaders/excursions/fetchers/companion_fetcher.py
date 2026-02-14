"""Загрузчик экскурсий с попутчиками"""
import logging
from typing import List, Optional
from datetime import datetime
from services.pelagos_api import PelagosAPI
from utils.cache_manager import CacheManager
from ..constants import CACHE_TTL_COMPANIONS, LOCATION_MAP
from ..transformers import CompanionTransformer, BaseTransformer

logger = logging.getLogger(__name__)


class CompanionFetcher:
    """Класс для загрузки экскурсий с попутчиками"""

    def __init__(self, api: PelagosAPI, cache: CacheManager):
        self.api = api
        self.cache = cache

    async def get_by_month(self, island: str, year: int, month: int) -> List[dict]:
        """
        Получить экскурсии с поиском попутчиков за месяц с кэшированием

        Args:
            island: код острова
            year: год
            month: месяц (1-12)

        Returns:
            список экскурсий с поиском попутчиков
        """
        # Проверяем кэш
        cache_key = f"companions:{island}:{year}-{month:02d}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"✓ Кэш HIT: {len(cached)} экскурсий с попутчиками")
            return cached

        try:
            # Формируем дату
            date_str = f"{year:04d}-{month:02d}-01"
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            api_date = dt.strftime("%d.%m.%Y")

            # Обработка island=None (для загрузки всех островов)
            if island:
                location_id = LOCATION_MAP.get(island.lower(), 0)
            else:
                location_id = 0  # 0 означает все острова

            # Получаем календарь
            days = await self.api.get_companions_calendar(location_id=location_id, date=api_date)

            logger.info(f"🔍 API вернул {len(days) if days else 0} дней")

            if not days:
                return []

            # Собираем экскурсии
            excursions = []
            total_processed = 0
            filtered_by_group_ex = 0
            filtered_by_subtype = 0

            for day_data in days:
                # Фильтруем по месяцу/году
                day_mon = day_data.get('mon')
                day_year = day_data.get('year')

                if day_mon and day_year:
                    if int(day_mon) != month or int(day_year) != year:
                        continue

                # Обрабатываем события
                for event_data in day_data.get('events', []):
                    total_processed += 1

                    # ФИЛЬТР: Пропускаем групповые экскурсии!
                    # Для поиска попутчиков показываем ТОЛЬКО индивидуальные экскурсии
                    service = event_data.get('service', {})

                    # Проверяем по group_ex (основной индикатор типа экскурсии)
                    # group_ex == 0 или None = индивидуальная
                    # group_ex > 0 = групповая
                    group_ex = service.get('group_ex')
                    subtype = service.get('subtype')

                    # Логируем для отладки
                    logger.debug(f"📌 Экскурсия: {service.get('name')}, group_ex={group_ex}, subtype={subtype}")

                    # Пропускаем ГРУППОВЫЕ экскурсии (group_ex > 0)
                    if group_ex is not None and group_ex > 0:
                        filtered_by_group_ex += 1
                        logger.debug(f"⏭️ Пропускаем групповую экскурсию (group_ex={group_ex}): {service.get('name')}")
                        continue

                    # Дополнительная проверка по subtype = 1110 (групповая)
                    if subtype == 1110:
                        filtered_by_subtype += 1
                        logger.debug(f"⏭️ Пропускаем групповую экскурсию (subtype=1110): {service.get('name')}")
                        continue

                    exc_dict = CompanionTransformer.transform(event_data, day_data)
                    if exc_dict:
                        excursions.append(exc_dict)
                        logger.debug(f"✅ Добавлено для попутчиков: {service.get('name')}")

            logger.info(f"📊 Статистика обработки попутчиков:")
            logger.info(f"  • Всего событий обработано: {total_processed}")
            logger.info(f"  • Отфильтровано по group_ex: {filtered_by_group_ex}")
            logger.info(f"  • Отфильтровано по subtype: {filtered_by_subtype}")
            logger.info(f"  ✅ Найдено экскурсий для '{island}': {len(excursions)}")

            # Кэшируем
            self.cache.set(cache_key, excursions, ttl=CACHE_TTL_COMPANIONS)

            return excursions

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки companions: {e}", exc_info=True)
            return []

    async def get_by_id(self, event_id: int) -> Optional[dict]:
        """
        Получить companion event по event_id с полными данными (slst)

        Args:
            event_id: ID события

        Returns:
            словарь с данными экскурсии или None
        """
        try:
            # Загружаем полные данные события
            companion_event = await self.api.get_companion_event_details(event_id)

            if not companion_event:
                return None

            # Формируем структуру
            today = datetime.now()
            day_data = {
                "date": today.strftime("%d.%m.%Y"),
                "mon": today.month,
                "year": str(today.year)
            }
            event_struct = {
                "id": event_id,
                "service_id": companion_event.get('id'),
                "service": companion_event,
                "pax": 0
            }

            # Преобразуем в dict
            exc_dict = CompanionTransformer.transform(event_struct, day_data)

            if exc_dict:
                # Добавляем цены
                price_list = BaseTransformer.extract_price_list(companion_event.get('rlst', []))
                exc_dict['price_list'] = price_list
                if price_list:
                    exc_dict['price_usd'] = min(price_list.values())

                # ГЛАВНОЕ: Добавляем попутчиков из slst
                slst = companion_event.get('slst', [])
                total_pax = sum(companion.get('pax', 0) for companion in slst)
                logger.info(f"📊 Попутчики для события {event_id}: найдено {len(slst)} записей, всего {total_pax} человек")
                exc_dict['pax'] = total_pax
                exc_dict['companions'] = slst

                return exc_dict

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки companion event {event_id}: {e}", exc_info=True)

        return None
