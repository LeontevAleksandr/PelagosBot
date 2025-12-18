"""Загрузчик данных для отелей"""
import logging
from typing import Optional, List
from services.pelagos_api import PelagosAPI
from services.schemas import Hotel, HotelRoom
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class HotelsLoader:
    """Класс для работы с отелями через Pelagos API"""

    # TTL для кэша (3 часа)
    CACHE_TTL = 10800

    def __init__(self, api: Optional[PelagosAPI] = None):
        self.api = api
        self.cache = get_cache_manager()

    async def get_all_locations(self) -> list:
        """
        Получить все доступные локации/острова из Pelagos API

        Returns:
            list: Список словарей с информацией о локациях
                [{id, name, code, parent, pics}, ...]
        """
        if not self.api:
            logger.warning("⚠️ API не инициализирован")
            return []

        # Проверяем кэш
        cache_key = "locations:all"
        cached_locations = self.cache.get(cache_key)

        if cached_locations:
            logger.info(f"✓ Используем кэш локаций ({len(cached_locations)} шт)")
            return cached_locations

        try:
            # Получаем все регионы из API
            regions = await self.api.get_regions()

            # Конвертируем в простой формат
            locations = []
            for region in regions:
                location_dict = {
                    'id': region.id,
                    'name': region.name,
                    'code': region.code,
                    'parent': region.parent,
                    'pics': region.pics if hasattr(region, 'pics') else []
                }
                locations.append(location_dict)

            # Кэшируем на 24 часа (локации меняются редко)
            self.cache.set(cache_key, locations, ttl=86400)

            logger.info(f"✅ Загружено {len(locations)} локаций из API")
            return locations

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки локаций: {e}")
            return []

    async def get_hotels_by_filters(
        self,
        island: str = None,
        stars: int = None,
        min_price: float = None,
        max_price: float = None,
        page: int = 0,
        per_page: int = None,
        check_in: str = None,
        check_out: str = None
    ) -> dict:
        
        logger.info(f"🔍 get_hotels_by_filters: island={island}, stars={stars}, page={page}, per_page={per_page}")

        if not self.api or not island:
            logger.warning(f"⚠️ Нет API или острова")
            return {'hotels': [], 'total': 0, 'page': 0, 'total_pages': 0}

        # Если указана пагинация - используем API пагинацию
        if per_page:
            # Если есть фильтр по звездам, загружаем с запасом
            if stars:
                # Пытаемся получить из кэша
                cache_key = f"hotels:filtered:{island}:{stars}"
                cached_filtered = self.cache.get(cache_key)

                if cached_filtered:
                    logger.info(f"✓ Используем кэш отфильтрованных отелей ({len(cached_filtered)} шт)")
                    filtered_hotels = [Hotel.from_dict(h) for h in cached_filtered]
                    # Сортируем кэшированные отели
                    filtered_hotels = sorted(filtered_hotels, key=lambda h: h.ord if h.ord else 0, reverse=True)
                else:
                    logger.info(f"📡 Загрузка всех отелей для фильтрации по {stars} звездам...")
                    all_hotels = await self.api.get_all_hotels(island)

                    # Фильтруем по звездам
                    filtered_hotels = [h for h in all_hotels if h.stars == stars]
                    logger.info(f"⭐ После фильтра по звездам: {len(filtered_hotels)} отелей из {len(all_hotels)}")

                    # Сортируем по рейтингу ДО кэширования
                    filtered_hotels = sorted(filtered_hotels, key=lambda h: h.ord if h.ord else 0, reverse=True)

                    # Кэшируем отфильтрованный и отсортированный список (без номеров)
                    filtered_dicts = [
                        {
                            'id': h.id,
                            'name': h.name,
                            'stars': h.stars,
                            'address': h.address,
                            'location': h.location,
                            'pics': h.pics,
                            'ord': h.ord
                        }
                        for h in filtered_hotels
                    ]
                    self.cache.set(cache_key, filtered_dicts, ttl=self.CACHE_TTL)

                # Применяем пагинацию к отфильтрованному и отсортированному списку
                start_idx = page * per_page
                end_idx = start_idx + per_page
                hotels = filtered_hotels[start_idx:end_idx]

                total_hotels = len(filtered_hotels)
                total_pages = (total_hotels + per_page - 1) // per_page if per_page else 1

                logger.info(f"✅ Страница {page+1}: отели {start_idx}-{end_idx-1} из {total_hotels}")
            else:
                # Без фильтра - используем прямую API пагинацию
                start = page * per_page
                logger.info(f"📡 Запрос отелей для {island} (start={start}, per_page={per_page})...")

                hotels_result = await self.api.get_hotels(island, perpage=per_page, start=start)
                hotels = hotels_result.get('hotels', [])
                pagination = hotels_result.get('pagination')

                total_hotels = pagination.total if pagination else len(hotels)
                total_pages = (total_hotels + per_page - 1) // per_page if per_page else 1

                logger.info(f"✅ Получено {len(hotels)} отелей (всего: {total_hotels})")
        else:
            # Загружаем все отели (старый способ)
            logger.info(f"📡 Запрос всех отелей для {island}...")
            hotels = await self.api.get_all_hotels(island)
            logger.info(f"✅ Получено {len(hotels)} отелей")

            # Фильтр по звездам
            if stars:
                hotels = [h for h in hotels if h.stars == stars]
                logger.info(f"⭐ После фильтра по звездам ({stars}): {len(hotels)} отелей")

            # Сортируем отели по рейтингу (ord) - от большего к меньшему
            if hotels:
                hotels = sorted(hotels, key=lambda h: h.ord if h.ord else 0, reverse=True)
                logger.info(f"📊 Отели отсортированы по рейтингу (ord)")

            total_hotels = len(hotels)
            total_pages = 1

        if not hotels:
            return {'hotels': [], 'total': 0, 'page': page, 'total_pages': 0}

        # Загружаем номера только для первого отеля (быстрый режим)
        result = []
        logger.info(f"⚡ Быстрая загрузка: получаем номера только для первого отеля")
        try:
            first_hotel = hotels[0]
            logger.info(f"   🏨 Загружаем: {first_hotel.name} (id={first_hotel.id})")

            # Пытаемся получить номера из кэша
            cache_key = f"hotel:rooms:{first_hotel.id}"
            cached_rooms = self.cache.get(cache_key)

            if cached_rooms:
                logger.info(f"      ✓ Используем кэш номеров ({len(cached_rooms)} шт)")
                rooms = [HotelRoom.from_dict(r) for r in cached_rooms]
            else:
                rooms = await self.api.get_all_rooms(first_hotel.id)
                logger.info(f"      ✓ Получено {len(rooms)} номеров")
                # Кэшируем номера
                rooms_dicts = [
                    {
                        'id': r.id,
                        'name': r.name,
                        'parent': r.parent,
                        'type': r.type
                    }
                    for r in rooms
                ]
                self.cache.set(cache_key, rooms_dicts, ttl=self.CACHE_TTL)

            # Используем async версию с загрузкой цен
            first_hotel_dict = await self._convert_hotel_async(
                first_hotel, rooms, load_prices=True, check_in=check_in, check_out=check_out
            )
            result.append(first_hotel_dict)
        except Exception as e:
            logger.error(f"      ❌ Ошибка: {e}")
            return {'hotels': [], 'total': 0, 'page': page, 'total_pages': 0}

        # Остальные отели - загружаем ограниченное количество (максимум 3 страницы = 15 отелей)
        import asyncio

        # Ограничиваем количество отелей для загрузки
        max_hotels_to_load = 14  # 15 - 1 (первый уже загружен)
        hotels_to_load = hotels[1:min(len(hotels), max_hotels_to_load + 1)]

        if hotels_to_load:
            logger.info(f"💰 Параллельная загрузка цен для {len(hotels_to_load)} отелей (ограничено 3 страницами)...")

            async def load_hotel_with_prices(hotel):
                """Загрузить номера и цены для отеля"""
                try:
                    cache_key = f"hotel:rooms:{hotel.id}"
                    cached_rooms = self.cache.get(cache_key)

                    if cached_rooms:
                        rooms = [HotelRoom.from_dict(r) for r in cached_rooms]
                    else:
                        rooms = await self.api.get_all_rooms(hotel.id)
                        # Кэшируем номера
                        rooms_dicts = [
                            {
                                'id': r.id,
                                'name': r.name,
                                'parent': r.parent,
                                'type': r.type
                            }
                            for r in rooms
                        ]
                        self.cache.set(cache_key, rooms_dicts, ttl=self.CACHE_TTL)

                    # Конвертируем С загрузкой цен
                    return await self._convert_hotel_async(
                        hotel, rooms, load_prices=True, check_in=check_in, check_out=check_out
                    )
                except Exception as e:
                    logger.error(f"   ❌ Ошибка для отеля {hotel.id}: {e}")
                    return self._convert_hotel(hotel, [])

            # Параллельная загрузка остальных отелей с ценами
            other_hotels_tasks = [load_hotel_with_prices(h) for h in hotels_to_load]
            other_hotels_data = await asyncio.gather(*other_hotels_tasks, return_exceptions=True)

            for hotel_data in other_hotels_data:
                if isinstance(hotel_data, Exception):
                    logger.error(f"   ❌ Ошибка загрузки отеля: {hotel_data}")
                else:
                    result.append(hotel_data)

        # Остальные отели - добавляем БЕЗ номеров и цен (будут загружены по требованию)
        remaining_hotels = hotels[max_hotels_to_load + 1:]
        if remaining_hotels:
            logger.info(f"📋 Добавляем {len(remaining_hotels)} отелей без цен (будут загружены по требованию)")
            for hotel in remaining_hotels:
                result.append(self._convert_hotel(hotel, []))

        logger.info(f"✅ Возвращаем {len(result)} отелей (total={total_hotels}, page={page}/{total_pages})")
        return {
            'hotels': result,
            'total': total_hotels,
            'page': page,
            'total_pages': total_pages
        }

    async def get_hotel_by_id(
        self,
        hotel_id: int,
        location_code: str = None,
        check_in: str = None,
        check_out: str = None
    ) -> Optional[dict]:
        
        if not self.api:
            logger.error("❌ API не инициализирован")
            return None

        if not location_code:
            logger.error(f"❌ get_hotel_by_id({hotel_id}) вызван БЕЗ location_code! Это критическая ошибка производительности.")
            return None

        try:
            # Получаем отели из конкретной локации с пагинацией
            hotel = None
            start = 0
            perpage = 100
            max_iterations = 5  # Защита: максимум 500 отелей (5 * 100)

            for iteration in range(max_iterations):
                hotels_result = await self.api.get_hotels(location_code, perpage=perpage, start=start)
                hotels = hotels_result.get('hotels', [])

                if not hotels:
                    break

                # Ищем нужный отель в текущей порции
                for h in hotels:
                    if h.id == hotel_id:
                        hotel = h
                        break

                if hotel:
                    break  # Нашли - выходим

                # Проверяем, есть ли еще отели
                pagination = hotels_result.get('pagination')
                if not pagination or (start + perpage >= pagination.total):
                    break

                start += perpage

            if not hotel:
                logger.warning(f"⚠️ Отель {hotel_id} не найден в локации {location_code}")
                return None

            # Загружаем номера с кэшированием
            cache_key = f"hotel:rooms:{hotel_id}"
            cached_rooms = self.cache.get(cache_key)

            if cached_rooms:
                logger.info(f"✓ Используем кэш номеров для отеля {hotel_id} ({len(cached_rooms)} шт)")
                rooms = [HotelRoom.from_dict(r) for r in cached_rooms]
            else:
                rooms = await self.api.get_all_rooms(hotel_id)
                # Кэшируем номера
                rooms_dicts = [
                    {
                        'id': r.id,
                        'name': r.name,
                        'parent': r.parent,
                        'type': r.type
                    }
                    for r in rooms
                ]
                self.cache.set(cache_key, rooms_dicts, ttl=self.CACHE_TTL)

            # Используем async версию с загрузкой цен
            return await self._convert_hotel_async(
                hotel, rooms, load_prices=True, check_in=check_in, check_out=check_out
            )

        except Exception as e:
            logger.error(f"❌ Ошибка get_hotel_by_id({hotel_id}, {location_code}): {e}")
            return None

    async def get_room_by_id(self, hotel_id: int, room_id: int) -> Optional[dict]:
        
        if not self.api:
            return None

        # Проверяем Redis кэш
        cache_key = f"hotel:rooms:{hotel_id}"
        cached_rooms = self.cache.get(cache_key)

        if cached_rooms:
            logger.debug(f"✓ Используем кэш номеров для отеля {hotel_id}")
            rooms = [HotelRoom.from_dict(r) for r in cached_rooms]
        else:
            # Загружаем и кэшируем все номера отеля
            rooms = await self.api.get_all_rooms(hotel_id)
            logger.debug(f"Загружено {len(rooms)} номеров для отеля {hotel_id}")

            # Кэшируем номера
            rooms_dicts = [
                {
                    'id': r.id,
                    'name': r.name,
                    'parent': r.parent,
                    'type': r.type
                }
                for r in rooms
            ]
            self.cache.set(cache_key, rooms_dicts, ttl=self.CACHE_TTL)

        # Ищем нужный номер
        for room in rooms:
            if room.id == room_id:
                return self._convert_room(room)

        return None

    async def _convert_hotel_async(
        self,
        hotel: Hotel,
        rooms: List[HotelRoom],
        load_prices: bool = True,
        check_in: str = None,
        check_out: str = None
    ) -> dict:
        
        # Параллельная загрузка цен для всех номеров
        rooms_data = []
        if load_prices and rooms:
            import asyncio
            if check_in and check_out:
                logger.info(f"🏨 Загрузка цен для {len(rooms)} номеров для {check_in} - {check_out}")
            else:
                logger.info(f"🏨 Загрузка цен для {len(rooms)} номеров")

            # Загружаем цены параллельно с учетом дат
            room_prices_tasks = [
                self._get_room_price(r.id, check_in, check_out)
                for r in rooms
            ]
            prices = await asyncio.gather(*room_prices_tasks, return_exceptions=True)

            # Проверяем уникальность цен
            unique_prices = set()
            for room, price in zip(rooms, prices):
                price_value = price if not isinstance(price, Exception) else None
                logger.info(f"   💰 Номер '{room.name}' (ID: {room.id}): ${price_value}")
                if price_value and price_value > 0:
                    unique_prices.add(price_value)
                rooms_data.append(self._convert_room(room, price_value))

            # Предупреждение если все цены одинаковые
            if len(unique_prices) == 1:
                logger.warning(f"⚠️ Все номера имеют одинаковую цену: ${list(unique_prices)[0]}")
            elif len(unique_prices) > 1:
                logger.info(f"✅ Найдено {len(unique_prices)} уникальных цен: {sorted(unique_prices)}")
        else:
            # Без цен
            rooms_data = [self._convert_room(r, None) for r in rooms]

        # Формируем URL фото (первое из массива pics)
        photo_url = None
        if hotel.pics and len(hotel.pics) > 0:
            pic = hotel.pics[0]
            if isinstance(pic, dict) and 'md5' in pic and 'ext' in pic:
                photo_url = f"https://app.pelagos.ru/pic/{pic['md5']}/{pic['md5']}.{pic['ext']}"

        return {
            'id': str(hotel.id),
            'name': hotel.name,
            'stars': hotel.stars or 0,
            'island_name': hotel.address or 'Не указан',
            'room_type': 'Стандарт',
            'rooms': rooms_data,
            'photo': photo_url,
            'pics': hotel.pics,  # Сохраняем весь массив на случай нужды
            'ord': hotel.ord or 0  # Рейтинг отеля
        }

    def _convert_hotel(self, hotel: Hotel, rooms: List[HotelRoom]) -> dict:
        """Преобразовать Hotel в dict для обработчика (синхронная версия без цен)"""
        # Формируем URL фото (первое из массива pics)
        photo_url = None
        if hotel.pics and len(hotel.pics) > 0:
            pic = hotel.pics[0]
            if isinstance(pic, dict) and 'md5' in pic and 'ext' in pic:
                photo_url = f"https://app.pelagos.ru/pic/{pic['md5']}/{pic['md5']}.{pic['ext']}"

        return {
            'id': str(hotel.id),
            'name': hotel.name,
            'stars': hotel.stars or 0,
            'island_name': hotel.address or 'Не указан',
            'room_type': 'Стандарт',
            'rooms': [self._convert_room(r, None) for r in rooms],
            'photo': photo_url,
            'pics': hotel.pics,  # Сохраняем весь массив на случай нужды
            'ord': hotel.ord or 0  # Рейтинг отеля
        }

    async def _get_room_price(self, room_id: int, check_in: str = None, check_out: str = None) -> float:
        
        try:
            from datetime import datetime

            # Проверяем кэш с учетом дат
            cache_key = f"room:price:{room_id}"
            if check_in and check_out:
                cache_key = f"room:price:{room_id}:{check_in}:{check_out}"

            cached_price = self.cache.get(cache_key)
            if cached_price is not None:
                logger.debug(f"✓ Используем кэш цены для номера {room_id}")
                return float(cached_price)

            data = await self.api.get_room_prices(room_id)
            room_prices = []

            logger.debug(f"📊 API вернул {len(data)} ценников для номера {room_id}")

            # Конвертируем даты пользователя в Unix timestamps
            check_in_ts = None
            check_out_ts = None
            if check_in:
                check_in_ts = int(datetime.strptime(check_in, "%Y-%m-%d").timestamp())
            if check_out:
                check_out_ts = int(datetime.strptime(check_out, "%Y-%m-%d").timestamp())

            # Обрабатываем массив ценников
            matched_schedules = 0
            for idx, price_obj in enumerate(data):
                sdt = price_obj.get('sdt')  # Начало периода действия цены
                edt = price_obj.get('edt')  # Окончание периода действия цены
                plst = price_obj.get('plst', [])

                # Если даты указаны, проверяем пересечение периодов
                if check_in_ts and check_out_ts:
                    if sdt and edt:
                        from_date = datetime.fromtimestamp(sdt).strftime('%Y-%m-%d')
                        to_date = datetime.fromtimestamp(edt).strftime('%Y-%m-%d')

                        # Проверяем ЛЮБОЕ пересечение периодов (более гибкая логика)
                        # Периоды пересекаются если: check_in <= edt И check_out >= sdt
                        if check_in_ts <= edt and check_out_ts >= sdt:
                            matched_schedules += 1

                            # Проверяем, полностью ли покрывает или частично
                            if sdt <= check_in_ts and edt >= check_out_ts:
                                logger.debug(f"   ✓ Ценник #{idx+1} подходит ПОЛНОСТЬЮ ({from_date} - {to_date})")
                            else:
                                logger.debug(f"   ⚠ Ценник #{idx+1} подходит ЧАСТИЧНО ({from_date} - {to_date})")
                        else:
                            logger.debug(f"   ✗ Ценник #{idx+1} пропущен (период {from_date} - {to_date})")
                            continue
                    else:
                        logger.debug(f"   ⚠ Ценник #{idx+1} без дат (sdt/edt)")
                else:
                    # Даты не указаны - берем все ценники
                    logger.debug(f"   ✓ Ценник #{idx+1} (даты не заданы)")

                # Обрабатываем компоненты ценника
                for comp_idx, price_component in enumerate(plst):
                    price = price_component.get('price', 0)
                    per = price_component.get('per')  # За что платим
                    period = price_component.get('period')  # Период оплаты

                    # per: 2 = за объект (номер), period: 2 = за день
                    # Берем ТОЛЬКО базовую цену номера, игнорируем доп. услуги (питание и т.д.)
                    # Список per: https://app.pelagos.ru/json-loadenum/per/
                    if per == 2 and price and price > 0:
                        room_prices.append(price)
                        logger.debug(f"      → Компонент #{comp_idx+1}: ${price} (per={per}, period={period})")
                    else:
                        # Пропускаем доп. услуги
                        logger.debug(f"      ✗ Пропущен компонент #{comp_idx+1}: ${price} (per={per} - не базовая цена)")

            # Возвращаем минимальную цену, если есть доступные цены
            if room_prices:
                min_price = min(room_prices)
                max_price = max(room_prices)
                period_info = f" для периода {check_in} - {check_out}" if check_in and check_out else ""

                if min_price == max_price:
                    logger.info(f"✓ Номер {room_id}{period_info}: ${min_price}/день")
                else:
                    logger.info(f"✓ Номер {room_id}{period_info}: ${min_price}-${max_price}/день (выбран min)")

                # Кэшируем полученную цену на 1 час
                self.cache.set(cache_key, min_price, ttl=3600)

                return min_price
            else:
                period_info = f" для периода {check_in} - {check_out}" if check_in and check_out else ""
                logger.warning(f"⚠️ Номер {room_id}{period_info}: цены не найдены (подходящих ценников: {matched_schedules})")

                # НЕ кэшируем нулевые цены - возможно, данные появятся позже
                return 0.0

        except Exception as e:
            logger.error(f"⚠️ Ошибка получения цены для номера {room_id}: {e}")
            return 0.0

    def _convert_room(self, room: HotelRoom, price: Optional[float] = None) -> dict:
        """Преобразовать HotelRoom в dict для обработчика"""
        return {
            'id': str(room.id),
            'name': room.name,
            'price': price if price is not None else 0  # Реальная цена или 0 если не загружена
        }
