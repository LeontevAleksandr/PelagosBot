"""Оптимизированный загрузчик данных для экскурсий с кэшированием и предзагрузкой"""
import logging
import asyncio
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from services.pelagos_api import PelagosAPI
from services.schemas import ExcursionEvent
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class ExcursionsLoader:
    """Класс для работы с экскурсиями через Pelagos API с оптимизацией производительности"""

    # TTL для разных типов кэша (в секундах)
    CACHE_TTL_GROUP = 3600  # 1 час для групповых
    CACHE_TTL_PRIVATE = 7200  # 2 часа для индивидуальных (меняются реже)
    CACHE_TTL_COMPANIONS = 3600  # 1 час для попутчиков

    # Маппинг островов (location ID → код острова)
    LOCATION_MAP = {
        "cebu": 9,
        "bohol": 10,
        "boracay": 8,
        "palawan": 11
    }

    # Русские названия островов (для старого API)
    ISLAND_NAMES = {
        "cebu": "Себу",
        "bohol": "Бохол",
        "boracay": "Боракай",
        "palawan": "Палаван"
    }

    # НОВЫЙ МАППИНГ: location ID → Русское название (для индивидуальных экскурсий)
    # Исключаем: 6 (родительский), 12 (другие острова)
    PRIVATE_ISLANDS_MAP = {
        7: "Манила",
        8: "Боракай",
        9: "Себу",
        10: "Бохол",
        11: "Палаван",
        13: "Корон",
        14: "Минданао",
        15: "Негрос",
        16: "Миндоро",
        18: "Виллы",
        37: "Моалбоал",
        38: "Малапаскуа",
        39: "Бантаян"
    }

    def __init__(self, api: Optional[PelagosAPI] = None):
        self.api = api
        self.cache = get_cache_manager()
        self._preload_tasks = {}  # Храним фоновые задачи предзагрузки

    def _get_island_info(self, location_id: int) -> tuple:
        """Получить код острова и название по location ID"""
        for code, lid in self.LOCATION_MAP.items():
            if lid == location_id:
                return code, self.ISLAND_NAMES.get(code, code.capitalize())
        return "cebu", "Себу"

    def _clean_html(self, html: str) -> str:
        """Очистить HTML от тегов и лишних пробелов"""
        if not html:
            return ""
        import re
        clean = re.sub('<.*?>', '', html)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def _build_photo_url(self, pic: dict) -> Optional[str]:
        """Построить URL фото из объекта pic"""
        if not pic or not isinstance(pic, dict):
            logger.debug(f"Photo pic is empty or not dict: {pic}")
            return None
        md5 = pic.get('md5')
        ext = pic.get('ext')
        if md5 and ext:
            photo_url = f"https://ru.pelagos.ru/pic/{md5}/{md5}.{ext}"
            logger.debug(f"Built photo URL: {photo_url}")
            return photo_url
        else:
            logger.debug(f"Missing md5 or ext in pic: md5={md5}, ext={ext}")
            return None

    def _extract_price_list(self, rlst: list) -> Dict[int, float]:
        """Извлечь список цен для разного количества человек из rlst"""
        price_list = {}
        if rlst and len(rlst) > 0:
            clst = rlst[0].get('clst', [])
            for item in clst:
                grp = item.get('grp')
                price = item.get('price')
                if grp and price:
                    price_list[grp] = price
        return price_list

    def _service_to_dict(self, service_data: dict, excursion_type: str = "private") -> Optional[dict]:
        """Преобразовать service из list API в dict для обработчиков (индивидуальные экскурсии)"""
        if not service_data:
            return None

        # Остров
        location = service_data.get('location', 9)
        island, island_name = self._get_island_info(location)

        # Фото
        pics = service_data.get('pics', [])
        photo_url = self._build_photo_url(pics[0]) if pics else None

        # Описание
        html = service_data.get('html', '')
        description = self._clean_html(html)

        # Цены
        min_price = service_data.get('min_price', 0)
        max_price = service_data.get('max_price', 0)
        price_list = self._extract_price_list(service_data.get('rlst', []))

        excursion_id = service_data.get('id')

        return {
            "id": str(excursion_id),
            "service_id": str(excursion_id),
            "name": service_data.get('name', ''),
            "island": island,
            "island_name": island_name,
            "location_id": location,  # НОВОЕ: сохраняем location_id для фильтрации
            "type": excursion_type,
            "date": None,
            "time": None,
            "duration": None,
            "description": description,
            "full_description": html,
            "price": min_price,
            "price_usd": min_price,
            "min_price": min_price,
            "max_price": max_price,
            "price_list": price_list,
            "people_count": 1,
            "photo": photo_url,
            "photos": pics,
            "url": f"https://ru.pelagos.ru/activity/{excursion_id}/" if excursion_id else "",
            "has_russian_guide": service_data.get('russian_guide') == 10,
            "private_transport": service_data.get('private_transport') == 10,
            "lunch_included": service_data.get('lunch_included') == 10,
            "tickets_included": service_data.get('tickets_included') == 10,
        }

    def _event_to_dict(self, event: ExcursionEvent, excursion_type: str = "group") -> Optional[dict]:
        """Преобразовать ExcursionEvent в dict для обработчиков (групповые экскурсии)"""
        if not event or not event.service:
            return None

        service = event.service

        # Дата и время
        date_str = None
        time_str = None
        if event.sdt:
            try:
                dt = datetime.fromtimestamp(event.sdt)
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            except Exception as e:
                logger.error(f"Ошибка конвертации timestamp {event.sdt}: {e}")

        # Остров
        location = getattr(service, 'location', 9)
        island, island_name = self._get_island_info(location)

        # Фото
        pic = getattr(service, 'pic', None)
        logger.debug(f"Group excursion event {event.id}, service {event.service_id}: pic = {pic}")
        photo_url = self._build_photo_url(pic)

        # Описание
        html = getattr(service, 'html', '')
        description = self._clean_html(html)[:200] if html else ""

        # Цена: используем min_price из service (минимальная цена для максимальной группы)
        # ИСПРАВЛЕНИЕ: Приоритет изменён на min_price > current.price > event.price
        # min_price - это минимальная цена за человека (для максимальной группы)
        # current.price - это цена для определённого количества людей (current.grp)
        price = 0

        # Сначала проверяем min_price - это правильная минимальная цена
        min_price = getattr(service, 'min_price', None)
        if min_price and min_price > 0:
            price = min_price
            logger.debug(f"Цена из min_price: ${price} для '{service.name}'")

        # Если нет min_price, берём из current (но это может быть цена для конкретной группы)
        if not price:
            current = getattr(service, 'current', None)
            if current and isinstance(current, dict):
                price = current.get('price', 0)
                grp = current.get('grp', 0)
                logger.debug(f"Цена из current: ${price} для {grp} чел. ('{service.name}')")

        # В крайнем случае - event.price
        if not price:
            price = event.price or 0
            if price:
                logger.debug(f"Цена из event.price: ${price} для '{service.name}'")

        # Получаем max_price если есть (для отображения диапазона)
        max_price = getattr(service, 'max_price', None)

        # НОВОЕ: Извлекаем price_list из rlst (список цен для разного количества людей)
        rlst = getattr(service, 'rlst', None)
        price_list = {}
        if rlst:
            price_list = self._extract_price_list(rlst)
            logger.debug(f"Price list для '{service.name}': {price_list}")

        return {
            "id": str(event.id),
            "service_id": str(event.service_id),
            "name": service.name,
            "island": island,
            "island_name": island_name,
            "type": excursion_type,
            "date": date_str,
            "time": time_str,
            "duration": event.duration // 60 if event.duration else None,
            "description": description,
            "full_description": html,
            "price": price,
            "price_usd": price,
            "min_price": price,  # Минимальная цена (для максимальной группы)
            "max_price": max_price,  # Максимальная цена (для 1 человека)
            "price_list": price_list,  # НОВОЕ: Список цен для разного количества людей
            "people_count": event.pax,
            "companions_count": event.pax,
            "photo": photo_url,
            "url": f"https://ru.pelagos.ru/group-tours-event/{event.id}/",
            "has_russian_guide": getattr(service, 'russian_guide', 0) == 10,
        }

    def _companion_event_to_dict(self, event_data: dict, day_data: dict) -> Optional[dict]:
        """Преобразовать event из flex API (попутчики) в dict"""
        if not event_data or not day_data:
            return None

        service = event_data.get('service', {})
        if not service:
            return None

        # Дата
        date_str = day_data.get('date', '')
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            formatted_date = dt.strftime("%Y-%m-%d")
        except:
            formatted_date = date_str

        # Остров
        location = service.get('location', 9)
        island, island_name = self._get_island_info(location)

        # Фото
        photo_url = self._build_photo_url(service.get('pic'))

        # Описание
        html = service.get('html', '')
        description = self._clean_html(html)

        event_id = event_data.get('id')
        service_id = service.get('id')

        # НОВОЕ: Список попутчиков (может отсутствовать в кратком списке)
        companions_list = event_data.get('slst', [])

        return {
            "id": str(event_id),
            "service_id": str(service_id),
            "event_id": str(event_id),
            "name": service.get('name', ''),
            "island": island,
            "island_name": island_name,
            "type": "companions",
            "date": formatted_date,
            "time": None,
            "duration": None,
            "description": description,
            "full_description": html,
            "price": 0,
            "price_usd": 0,
            "photo": photo_url,
            "url": f"https://ru.pelagos.ru/activity/{service_id}/",
            "pax": event_data.get('pax', 0),
            "companions": companions_list,  # НОВОЕ: Добавляем список попутчиков
            "has_russian_guide": service.get('russian_guide') == 10,
            "private_transport": service.get('private_transport') == 10,
            "lunch_included": service.get('lunch_included') == 10,
            "tickets_included": service.get('tickets_included') == 10,
        }

    async def get_available_islands_with_count(self) -> List[Dict[str, any]]:
        """
        НОВАЯ ФУНКЦИЯ: Загрузить все доступные острова с подсчётом индивидуальных экскурсий

        Returns:
            Список словарей: [{"location_id": int, "name": str, "count": int}, ...]
            Отсортирован по количеству экскурсий (от большего к меньшему)
        """
        if not self.api:
            logger.warning("⚠️ API не инициализирован")
            return []

        # Проверяем кэш
        cache_key = "islands_with_count"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"✓ Кэш HIT: {len(cached)} островов с подсчётом")
            return cached

        try:
            logger.info("🔍 Загрузка всех индивидуальных экскурсий для подсчёта островов...")

            # Загружаем ВСЕ индивидуальные экскурсии с location=0
            tomorrow = datetime.now() + timedelta(days=1)
            api_date = tomorrow.strftime("%d.%m.%Y")

            services = await self.api.get_private_excursions(
                location_id=0,
                date=api_date
            )

            logger.info(f"📡 API вернул {len(services)} индивидуальных экскурсий")

            # Конвертируем все сервисы в словари и кэшируем их сразу
            all_excursions = []
            for service in services:
                exc_dict = self._service_to_dict(service, "private")
                if exc_dict:
                    all_excursions.append(exc_dict)

            # Кэшируем ВСЕ экскурсии для дальнейшего использования
            self.cache.set("all_private_excursions", all_excursions, ttl=self.CACHE_TTL_PRIVATE)
            logger.info(f"💾 Закэшировано {len(all_excursions)} индивидуальных экскурсий")

            # Подсчитываем экскурсии по островам
            island_counts = {}
            for service in services:
                location_id = service.get('location')

                # Фильтруем только наши острова (исключаем 6 и 12)
                if location_id in self.PRIVATE_ISLANDS_MAP:
                    if location_id not in island_counts:
                        island_counts[location_id] = 0
                    island_counts[location_id] += 1

            # Формируем результат
            islands = []
            for location_id, count in island_counts.items():
                islands.append({
                    "location_id": location_id,
                    "name": self.PRIVATE_ISLANDS_MAP[location_id],
                    "count": count
                })

            # Сортируем по количеству экскурсий (от большего к меньшему)
            islands.sort(key=lambda x: x['count'], reverse=True)

            logger.info(f"✅ Найдено {len(islands)} островов с экскурсиями:")
            for island in islands:
                logger.info(f"  • {island['name']}: {island['count']} экскурсий")

            # Кэшируем с увеличенным TTL
            self.cache.set(cache_key, islands, ttl=self.CACHE_TTL_PRIVATE)

            return islands

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки островов с подсчётом: {e}", exc_info=True)
            return []

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
            return await self._get_private_excursions_filtered(island=island)

        # Проверяем кэш для групповых
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
                exc_dict = self._event_to_dict(event, excursion_type or "group")
                if exc_dict:
                    excursions.append(exc_dict)

            # Кэшируем
            self.cache.set(cache_key, excursions, ttl=self.CACHE_TTL_GROUP)

            logger.info(f"✅ Возвращаем {len(excursions)} экскурсий")
            return excursions

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки экскурсий: {e}", exc_info=True)
            return []

    async def _get_private_excursions_filtered(self, island: str = None) -> list:
        """
        Получить индивидуальные экскурсии с кэшированием

        Args:
            island: location_id в виде строки (например, "9" для Себу) или None для всех
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
                        logger.info(f"✓ Кэш HIT: {len(cached)} экскурсий для острова {self.PRIVATE_ISLANDS_MAP.get(location_id, location_id)}")
                        return cached

                    logger.info(f"🔍 Загрузка индивидуальных экскурсий для location_id={location_id} ({self.PRIVATE_ISLANDS_MAP.get(location_id, location_id)})")

                    # Делаем API запрос с фильтром по location_id
                    tomorrow = datetime.now() + timedelta(days=1)
                    api_date = tomorrow.strftime("%d.%m.%Y")

                    services = await self.api.get_private_excursions(
                        location_id=location_id,
                        date=api_date
                    )

                    logger.info(f"📡 API вернул {len(services)} индивидуальных экскурсий для острова {location_id}")

                    # Конвертируем services в словари
                    excursions = []
                    for service in services:
                        exc_dict = self._service_to_dict(service, "private")
                        if exc_dict:
                            excursions.append(exc_dict)

                    # Кэшируем результат для этого острова
                    self.cache.set(cache_key, excursions, ttl=self.CACHE_TTL_PRIVATE)

                    logger.info(f"✅ Возвращаем {len(excursions)} индивидуальных экскурсий для острова {self.PRIVATE_ISLANDS_MAP.get(location_id, location_id)}")
                    return excursions

                except ValueError:
                    # Если передан старый формат (код острова типа "cebu")
                    location_id = self.LOCATION_MAP.get(island.lower(), 0)
                    logger.info(f"🔍 Загрузка индивидуальных экскурсий (старый формат): {island} (id={location_id})")

                    tomorrow = datetime.now() + timedelta(days=1)
                    api_date = tomorrow.strftime("%d.%m.%Y")

                    services = await self.api.get_private_excursions(
                        location_id=location_id,
                        date=api_date
                    )

                    excursions = [
                        exc for exc in (self._service_to_dict(s, "private") for s in services)
                        if exc and exc.get('island') == island.lower()
                    ]

                    logger.info(f"✅ Возвращаем {len(excursions)} индивидуальных экскурсий")
                    return excursions
            else:
                # Если остров не указан - загружаем все экскурсии через общий кэш
                all_excursions = self.cache.get("all_private_excursions")

                if not all_excursions:
                    # Если нет в кэше - загружаем через get_available_islands_with_count
                    # Эта функция автоматически закэширует все экскурсии
                    logger.info("🔄 Кэш пуст, загружаем все экскурсии...")
                    await self.get_available_islands_with_count()
                    all_excursions = self.cache.get("all_private_excursions") or []

                # Возвращаем все экскурсии
                logger.info(f"✅ Возвращаем все {len(all_excursions)} индивидуальных экскурсий")
                return all_excursions

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки индивидуальных экскурсий: {e}", exc_info=True)
            return []

    async def preload_private_excursions(self, island: str = None):
        """
        НОВАЯ ФУНКЦИЯ: Предзагрузка индивидуальных экскурсий в фоне

        Использование: вызывать при выборе острова/типа экскурсии
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
        task = asyncio.create_task(self._get_private_excursions_filtered(island))
        self._preload_tasks[cache_key] = task

        # Очищаем задачу после выполнения
        def cleanup(_):
            self._preload_tasks.pop(cache_key, None)
        task.add_done_callback(cleanup)

    async def get_excursion_by_id(self, excursion_id: str) -> Optional[dict]:
        """
        Получить экскурсию по ID с кэшированием

        ОПТИМИЗАЦИЯ: сначала проверяем кэш, затем пробуем найти в общих кэшах,
        только потом идем в API
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
            event = await self.api.get_excursion_event_details(service_id)
            if event:
                exc_dict = self._event_to_dict(event)
                self.cache.set(cache_key, exc_dict, ttl=self.CACHE_TTL_GROUP)
                return exc_dict

            # Пробуем как companion event
            companion_event = await self.api.get_companion_event_details(service_id)
            if companion_event:
                today = datetime.now()
                day_data = {
                    "date": today.strftime("%d.%m.%Y"),
                    "mon": today.month,
                    "year": str(today.year)
                }
                event_struct = {
                    "id": service_id,
                    "service_id": companion_event.get('id'),
                    "service": companion_event,
                    "pax": 0
                }
                exc_dict = self._companion_event_to_dict(event_struct, day_data)

                if exc_dict:
                    # Добавляем цены и попутчиков
                    price_list = self._extract_price_list(companion_event.get('rlst', []))
                    exc_dict['price_list'] = price_list
                    if price_list:
                        exc_dict['price_usd'] = min(price_list.values())

                    slst = companion_event.get('slst', [])
                    exc_dict['pax'] = len(slst)
                    exc_dict['companions'] = slst

                    self.cache.set(cache_key, exc_dict, ttl=self.CACHE_TTL_COMPANIONS)
                    return exc_dict

            # ОПТИМИЗАЦИЯ: проверяем кэши индивидуальных экскурсий для конкретных островов
            # перед загрузкой из API

            # 1. Проверяем кэши для конкретных островов (новый формат)
            for location_id in self.PRIVATE_ISLANDS_MAP.keys():
                island_cache_key = f"private_excursions_island_{location_id}"
                island_cached = self.cache.get(island_cache_key)
                if island_cached:
                    for exc in island_cached:
                        if exc.get('id') == str(service_id) or exc.get('service_id') == str(service_id):
                            self.cache.set(cache_key, exc, ttl=self.CACHE_TTL_PRIVATE)
                            logger.info(f"✓ Найдена индивидуальная экскурсия {service_id}")
                            return exc

            # 2. Проверяем общий кэш (старый формат)
            all_private_cache = self.cache.get("all_private_excursions")
            if all_private_cache:
                for exc in all_private_cache:
                    if exc.get('id') == str(service_id) or exc.get('service_id') == str(service_id):
                        self.cache.set(cache_key, exc, ttl=self.CACHE_TTL_PRIVATE)
                        logger.info(f"✓ Найдена индивидуальная экскурсия {service_id}")
                        return exc

            # Если не нашли в кэше - загружаем все индивидуальные экскурсии
            tomorrow = datetime.now() + timedelta(days=1)
            api_date = tomorrow.strftime("%d.%m.%Y")

            logger.info(f"⚠️ Экскурсия {service_id} не найдена в кэше, загружаем все индивидуальные экскурсии...")
            services = await self.api.get_private_excursions(location_id=0, date=api_date)

            for service_data in services:
                if service_data.get('id') == service_id:
                    exc_dict = self._service_to_dict(service_data, "private")
                    self.cache.set(cache_key, exc_dict, ttl=self.CACHE_TTL_PRIVATE)
                    logger.info(f"✓ Найдена индивидуальная экскурсия {excursion_id}")
                    return exc_dict

            logger.warning(f"⚠️ Экскурсия {excursion_id} не найдена")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки экскурсии {excursion_id}: {e}", exc_info=True)
            return None

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
        if not self.api:
            return []

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

            # ИСПРАВЛЕНО: Обработка island=None (для загрузки всех островов)
            if island:
                location_id = self.LOCATION_MAP.get(island.lower(), 0)
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

                    exc_dict = self._companion_event_to_dict(event_data, day_data)
                    # ИСПРАВЛЕНИЕ: Не фильтруем по острову, так как API уже вернул события
                    # для нужной локации (параметр location в запросе).
                    if exc_dict:
                        excursions.append(exc_dict)
                        logger.debug(f"✅ Добавлено для попутчиков: {service.get('name')}")

            logger.info(f"📊 Статистика обработки попутчиков:")
            logger.info(f"  • Всего событий обработано: {total_processed}")
            logger.info(f"  • Отфильтровано по group_ex: {filtered_by_group_ex}")
            logger.info(f"  • Отфильтровано по subtype: {filtered_by_subtype}")
            logger.info(f"  ✅ Найдено экскурсий для '{island}': {len(excursions)}")

            # Кэшируем
            self.cache.set(cache_key, excursions, ttl=self.CACHE_TTL_COMPANIONS)

            return excursions

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки companions: {e}", exc_info=True)
            return []
