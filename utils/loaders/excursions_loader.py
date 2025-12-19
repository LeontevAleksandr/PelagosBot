"""Загрузчик данных для экскурсий"""
import logging
from typing import Optional, List
from datetime import datetime
from services.pelagos_api import PelagosAPI
from services.schemas import ExcursionEvent
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class ExcursionsLoader:
    """Класс для работы с экскурсиями через Pelagos API"""

    # TTL для кэша (1 час - экскурсии обновляются чаще)
    CACHE_TTL = 3600

    def __init__(self, api: Optional[PelagosAPI] = None):
        self.api = api
        self.cache = get_cache_manager()

    def _convert_event_to_dict(self, event: ExcursionEvent, excursion_type: str = "group") -> dict:
        """
        Преобразовать ExcursionEvent в dict для обработчиков

        Args:
            event: объект ExcursionEvent
            excursion_type: тип экскурсии (group, private, companions)

        Returns:
            словарь с данными экскурсии в формате старого API
        """
        if not event or not event.service:
            return None

        service = event.service

        # Конвертируем Unix timestamp в дату YYYY-MM-DD
        date_str = None
        if event.sdt:
            try:
                dt = datetime.fromtimestamp(event.sdt)
                date_str = dt.strftime("%Y-%m-%d")
            except:
                logger.error(f"Ошибка конвертации timestamp {event.sdt}")

        # Формируем URL фото
        photo_url = None
        if hasattr(service, 'pic') and service.pic:
            pic = service.pic
            if isinstance(pic, dict) and 'md5' in pic and 'ext' in pic:
                photo_url = f"https://ru.pelagos.ru/pic/{pic['md5']}/{pic['md5']}.{pic['ext']}"

        # Определяем остров по location
        island = "cebu"  # По умолчанию
        if hasattr(service, 'location'):
            location_map = {
                9: "cebu",
                10: "bohol",
                8: "boracay"
            }
            island = location_map.get(service.location, "cebu")

        # Извлекаем короткое описание из HTML
        description = ""
        if hasattr(service, 'html') and service.html:
            # Берем первые 200 символов текста (очищенного от HTML)
            import re
            clean_text = re.sub('<.*?>', '', service.html)
            description = clean_text[:200].strip()

        # Определяем название острова для отображения
        island_names = {
            "cebu": "Себу",
            "bohol": "Бохол",
            "boracay": "Боракай"
        }
        island_name = island_names.get(island, island.capitalize() if island else "Не указан")

        # Цена по умолчанию (если не указана в API)
        # TODO: Получать реальные цены из другого endpoint
        default_price = 5500  # Примерная цена групповой экскурсии

        return {
            "id": str(event.id),  # ID события
            "service_id": str(event.service_id),  # ID услуги
            "name": service.name,
            "island": island,
            "island_name": island_name,  # Для отображения
            "type": excursion_type,
            "date": date_str,
            "time": datetime.fromtimestamp(event.sdt).strftime("%H:%M") if event.sdt else None,
            "duration": event.duration // 60 if event.duration else None,  # В минутах -> часы
            "description": description,
            "full_description": service.html if hasattr(service, 'html') else None,
            "price": event.price if event.price > 0 else default_price,
            "price_usd": event.price if event.price > 0 else default_price,  # Для совместимости
            "people_count": event.pax,
            "companions_count": event.pax,  # Для companions
            "photo": photo_url,
            "url": f"https://ru.pelagos.ru/group-tours-event/{event.id}/",
            "has_russian_guide": service.russian_guide == 10 if hasattr(service, 'russian_guide') else False,
        }

    async def get_excursions_by_filters(
        self,
        island: str = None,
        excursion_type: str = None,
        date: str = None
    ) -> list:
        """
        Получить экскурсии по фильтрам

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

        # Проверяем кэш
        cache_key = f"excursions:{island or 'all'}:{excursion_type or 'all'}:{date or 'all'}"
        cached_excursions = self.cache.get(cache_key)

        if cached_excursions:
            logger.info(f"✓ Используем кэш экскурсий ({len(cached_excursions)} шт)")
            return cached_excursions

        try:
            logger.info(f"🔍 Загрузка экскурсий: island={island}, type={excursion_type}, date={date}")

            # Получаем экскурсии из API
            events = await self.api.get_excursions_by_location_and_date(
                location_code=island,
                date=date
            )

            logger.info(f"📡 Получено {len(events)} событий из API")

            # Конвертируем в формат для обработчиков
            excursions = []
            for event in events:
                # Фильтруем по типу если указан
                # Пока все экскурсии из calendar - групповые
                if excursion_type and excursion_type != "group":
                    continue

                excursion_dict = self._convert_event_to_dict(event, excursion_type or "group")
                if excursion_dict:
                    excursions.append(excursion_dict)

            # Кэшируем результат
            self.cache.set(cache_key, excursions, ttl=self.CACHE_TTL)

            logger.info(f"✅ Возвращаем {len(excursions)} экскурсий")
            return excursions

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки экскурсий: {e}")
            return []

    async def get_excursion_by_id(self, excursion_id: str) -> Optional[dict]:
        """
        Получить экскурсию по ID

        Args:
            excursion_id: ID экскурсии (event_id)

        Returns:
            словарь с данными экскурсии или None
        """
        if not self.api:
            return None

        # Проверяем кэш
        cache_key = f"excursion:{excursion_id}"
        cached_excursion = self.cache.get(cache_key)

        if cached_excursion:
            logger.info(f"✓ Используем кэш экскурсии {excursion_id}")
            return cached_excursion

        try:
            # Конвертируем ID в int
            event_id = int(excursion_id)

            # Получаем детальную информацию
            event = await self.api.get_excursion_event_details(event_id)

            if not event:
                logger.warning(f"⚠️ Экскурсия {excursion_id} не найдена")
                return None

            # Конвертируем в dict
            excursion_dict = self._convert_event_to_dict(event)

            # Кэшируем
            self.cache.set(cache_key, excursion_dict, ttl=self.CACHE_TTL)

            return excursion_dict

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки экскурсии {excursion_id}: {e}")
            return None

    async def get_companions_by_month(self, island: str, year: int, month: int) -> list:
        """
        Получить экскурсии с поиском попутчиков за месяц

        Args:
            island: код острова
            year: год
            month: месяц (1-12)

        Returns:
            список экскурсий с поиском попутчиков
        """
        if not self.api:
            return []

        try:
            # Формируем дату первого дня месяца
            date_str = f"{year:04d}-{month:02d}-01"

            # Получаем календарь на месяц
            from datetime import datetime
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            api_date = dt.strftime("%d.%m.%Y")

            # Маппинг островов на ID
            location_map = {
                "cebu": 9,
                "bohol": 10,
                "boracay": 8
            }
            location_id = location_map.get(island.lower(), 0)

            months = await self.api.get_group_tours_calendar(date=api_date, location=location_id)

            if not months:
                return []

            # Собираем все экскурсии за месяц
            excursions = []
            for month_obj in months:
                # Проверяем, что это нужный месяц
                if int(month_obj.year) != year:
                    continue

                for day in month_obj.days:
                    for event in day.events:
                        # Для companions - используем те же групповые экскурсии
                        # но с типом "companions"
                        excursion_dict = self._convert_event_to_dict(event, "companions")
                        if excursion_dict:
                            excursions.append(excursion_dict)

            return excursions

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки companions: {e}")
            return []
