"""Загрузчик данных из JSON (MVP) и адаптер для Pelagos API"""
import json
import os
import logging
from typing import Optional, List
from services.pelagos_api import PelagosAPI
from services.schemas import Hotel, HotelRoom
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class DataLoader:
    """Класс для работы с mock данными и Pelagos API"""

    def __init__(self, api: Optional[PelagosAPI] = None, json_path: str = "data/mock_data.json"):
        self.api = api
        self.json_path = json_path
        self.data = self._load_data()
        # Кэш для номеров отелей: {hotel_id: [rooms]}
        self._rooms_cache = {}
        # Redis кэш-менеджер
        self.cache = get_cache_manager()

    def _load_data(self) -> dict:
        """Загрузить данные из JSON"""
        if not os.path.exists(self.json_path):
            return {
                "hotels_count": 150,
                "hotels": [],
                "users": {},
                "orders": []
            }

        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_hotels_count(self) -> int:
        """Получить количество отелей"""
        return self.data.get("hotels_count", 150)

    async def get_hotels_by_filters(
        self,
        island: str = None,
        stars: int = None,
        min_price: float = None,
        max_price: float = None,
        load_first_only: bool = True,
        page: int = 0,
        per_page: int = None
    ) -> dict:
        """
        Получить отели по фильтрам (из Pelagos API)

        Args:
            island: код острова
            stars: количество звезд
            min_price: минимальная цена
            max_price: максимальная цена
            load_first_only: загрузить только первый отель с номерами (для быстрого отображения)
            page: номер страницы (0-based)
            per_page: количество отелей на странице (None = все отели)

        Returns:
            dict: {
                'hotels': list - список отелей (первый - с номерами, остальные - без),
                'total': int - общее количество отелей,
                'page': int - текущая страница,
                'total_pages': int - всего страниц
            }
        """
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
                else:
                    logger.info(f"📡 Загрузка всех отелей для фильтрации по {stars} звездам...")
                    all_hotels = await self.api.get_all_hotels(island)

                    # Фильтруем по звездам
                    filtered_hotels = [h for h in all_hotels if h.stars == stars]
                    logger.info(f"⭐ После фильтра по звездам: {len(filtered_hotels)} отелей из {len(all_hotels)}")

                    # Кэшируем отфильтрованный список (без номеров) на 10 минут
                    filtered_dicts = [
                        {
                            'id': h.id,
                            'name': h.name,
                            'stars': h.stars,
                            'address': h.address,
                            'location': h.location
                        }
                        for h in filtered_hotels
                    ]
                    self.cache.set(cache_key, filtered_dicts, ttl=600)

                # Применяем пагинацию к отфильтрованному списку
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

            total_hotels = len(hotels)
            total_pages = 1

        if not hotels:
            return {'hotels': [], 'total': 0, 'page': page, 'total_pages': 0}

        # Загружаем номера только для первого отеля
        result = []
        if load_first_only:
            logger.info(f"⚡ Быстрая загрузка: получаем номера только для первого отеля")
            try:
                first_hotel = hotels[0]
                logger.info(f"   🏨 Загружаем: {first_hotel.name} (id={first_hotel.id})")
                rooms = await self.api.get_all_rooms(first_hotel.id)
                logger.info(f"      ✓ Получено {len(rooms)} номеров")
                result.append(self._convert_hotel(first_hotel, rooms))
            except Exception as e:
                logger.error(f"      ❌ Ошибка: {e}")
                return {'hotels': [], 'total': 0, 'page': page, 'total_pages': 0}

            # Остальные отели - без номеров (загрузим позже по запросу)
            for hotel in hotels[1:]:
                result.append(self._convert_hotel(hotel, []))

        else:
            # Загружаем все отели с номерами (с кэшированием)
            logger.info(f"⏳ Полная загрузка: получаем номера для всех {len(hotels)} отелей...")
            for i, hotel in enumerate(hotels):
                try:
                    # Пытаемся получить номера из кэша
                    cache_key = f"hotel:rooms:{hotel.id}"
                    cached_rooms = self.cache.get(cache_key)

                    if cached_rooms:
                        logger.debug(f"✓ Используем кэш номеров для отеля {hotel.id}")
                        rooms = [HotelRoom.from_dict(r) for r in cached_rooms]
                    else:
                        rooms = await self.api.get_all_rooms(hotel.id)
                        # Кэшируем номера на 10 минут
                        rooms_dicts = [
                            {
                                'id': r.id,
                                'name': r.name,
                                'parent': r.parent,
                                'type': r.type
                            }
                            for r in rooms
                        ]
                        self.cache.set(cache_key, rooms_dicts, ttl=600)

                    result.append(self._convert_hotel(hotel, rooms))
                    if (i + 1) % 5 == 0:
                        logger.info(f"   📊 Обработано {i+1}/{len(hotels)}")
                except Exception as e:
                    logger.error(f"   ❌ Ошибка для отеля {hotel.id}: {e}")
                    continue

        logger.info(f"✅ Возвращаем {len(result)} отелей (total={total_hotels}, page={page}/{total_pages})")
        return {
            'hotels': result,
            'total': total_hotels,
            'page': page,
            'total_pages': total_pages
        }

    async def get_hotel_by_id(self, hotel_id: int, location_code: str = None) -> Optional[dict]:
        """
        Получить отель по ID (из Pelagos API)

        Args:
            hotel_id: ID отеля
            location_code: код локации для оптимизации поиска (ОБЯЗАТЕЛЬНО для производительности!)
        """
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

            # Загружаем номера
            rooms = await self.api.get_all_rooms(hotel_id)

            # Используем async версию с загрузкой цен
            return await self._convert_hotel_async(hotel, rooms, load_prices=True)

        except Exception as e:
            logger.error(f"❌ Ошибка get_hotel_by_id({hotel_id}, {location_code}): {e}")
            return None

    async def get_room_by_id(self, hotel_id: int, room_id: int) -> Optional[dict]:
        """
        Получить номер по ID (из Pelagos API с кэшированием)

        Args:
            hotel_id: ID отеля
            room_id: ID номера

        Returns:
            dict с данными номера или None
        """
        if not self.api:
            return None

        # Проверяем кэш
        if hotel_id not in self._rooms_cache:
            # Загружаем и кэшируем все номера отеля
            rooms = await self.api.get_all_rooms(hotel_id)
            self._rooms_cache[hotel_id] = rooms
            logger.debug(f"Кэшировано {len(rooms)} номеров для отеля {hotel_id}")
        else:
            rooms = self._rooms_cache[hotel_id]
            logger.debug(f"Использован кэш номеров для отеля {hotel_id}")

        # Ищем нужный номер
        for room in rooms:
            if room.id == room_id:
                return self._convert_room(room)

        return None

    async def _convert_hotel_async(self, hotel: Hotel, rooms: List[HotelRoom], load_prices: bool = True) -> dict:
        """
        Преобразовать Hotel в dict для обработчика (с async загрузкой цен)

        Args:
            hotel: объект отеля
            rooms: список номеров
            load_prices: загружать ли реальные цены (если False - будет 0)
        """
        # Параллельная загрузка цен для всех номеров
        rooms_data = []
        if load_prices and rooms:
            import asyncio
            # Загружаем цены параллельно
            room_prices_tasks = [self._get_room_price(r.id) for r in rooms]
            prices = await asyncio.gather(*room_prices_tasks, return_exceptions=True)

            for room, price in zip(rooms, prices):
                rooms_data.append(self._convert_room(room, price if not isinstance(price, Exception) else None))
        else:
            # Без цен
            rooms_data = [self._convert_room(r, None) for r in rooms]

        return {
            'id': str(hotel.id),
            'name': hotel.name,
            'stars': hotel.stars or 0,
            'island_name': hotel.address or 'Не указан',
            'room_type': 'Стандарт',
            'rooms': rooms_data
        }

    def _convert_hotel(self, hotel: Hotel, rooms: List[HotelRoom]) -> dict:
        """Преобразовать Hotel в dict для обработчика (синхронная версия без цен)"""
        return {
            'id': str(hotel.id),
            'name': hotel.name,
            'stars': hotel.stars or 0,
            'island_name': hotel.address or 'Не указан',
            'room_type': 'Стандарт',
            'rooms': [self._convert_room(r, None) for r in rooms]
        }

    async def _get_room_price(self, room_id: int) -> float:
        """Получить цену номера из API"""
        try:
            room_prices = await self.api.get_room_prices(room_id)
            if room_prices and hasattr(room_prices, 'price'):
                return float(room_prices.price)
        except Exception as e:
            logger.debug(f"⚠️ Не удалось получить цену для номера {room_id}: {e}")
        return 0.0

    def _convert_room(self, room: HotelRoom, price: Optional[float] = None) -> dict:
        """Преобразовать HotelRoom в dict для обработчика"""
        return {
            'id': str(room.id),
            'name': room.name,
            'price': price if price is not None else 0  # Реальная цена или 0 если не загружена
        }

    # ========== ЭКСКУРСИИ ==========
    
    def get_excursions_by_filters(
        self,
        island: str = None,
        excursion_type: str = None,
        date: str = None
    ) -> list:
        """
        Получить экскурсии по фильтрам
        
        Args:
            island: код острова
            excursion_type: тип экскурсии (group, private, companions)
            date: дата в формате YYYY-MM-DD (для групповых и companions)
        """
        excursions = self.data.get("excursions", [])
        
        # Фильтр по острову
        if island:
            excursions = [e for e in excursions if e["island"] == island]
        
        # Фильтр по типу
        if excursion_type:
            excursions = [e for e in excursions if e["type"] == excursion_type]
        
        # Фильтр по дате (для групповых и companions)
        if date:
            excursions = [e for e in excursions if e.get("date") == date]
        
        return excursions
    
    def get_excursion_by_id(self, excursion_id: str) -> dict:
        """Получить экскурсию по ID"""
        excursions = self.data.get("excursions", [])
        for excursion in excursions:
            if excursion["id"] == excursion_id:
                return excursion
        return None
    
    def get_companions_by_month(self, island: str, year: int, month: int) -> list:
        """Получить экскурсии с поиском попутчиков за месяц"""
        from datetime import datetime
        
        excursions = self.get_excursions_by_filters(island=island, excursion_type="companions")
        
        # Фильтруем по месяцу
        result = []
        for exc in excursions:
            if exc.get("date"):
                try:
                    exc_date = datetime.strptime(exc["date"], "%Y-%m-%d")
                    if exc_date.year == year and exc_date.month == month:
                        result.append(exc)
                except:
                    pass
        
        return result
    
    # ========== ПАКЕТНЫЕ ТУРЫ ==========
    
    def get_packages_by_date(self, target_date: str = None) -> list:
        """
        Получить пакетные туры близкие к указанной дате
        
        Args:
            target_date: дата в формате YYYY-MM-DD (если None - все туры)
        """
        from datetime import datetime, timedelta
        
        packages = self.data.get("packages", [])
        
        if not target_date:
            return packages
        
        # Ищем туры, которые начинаются в пределах ±30 дней от указанной даты
        target = datetime.strptime(target_date, "%Y-%m-%d")
        result = []
        
        for pkg in packages:
            try:
                start_date = datetime.strptime(pkg["start_date"], "%Y-%m-%d")
                diff = abs((start_date - target).days)
                
                if diff <= 30:  # В пределах месяца
                    result.append(pkg)
            except:
                pass
        
        # Сортируем по близости к дате
        result.sort(key=lambda p: abs((datetime.strptime(p["start_date"], "%Y-%m-%d") - target).days))
        
        return result
    
    def get_package_by_id(self, package_id: str) -> dict:
        """Получить пакетный тур по ID"""
        packages = self.data.get("packages", [])
        for package in packages:
            if package["id"] == package_id:
                return package
        return None

    # ========== ТРАНСФЕРЫ ==========

    def get_transfers_by_island(self, island: str = None) -> list:
        """
        Получить трансферы по острову

        Args:
            island: код острова (если None - все трансферы)
        """
        transfers = self.data.get("transfers", [])

        if not island:
            return transfers

        # Фильтр по острову
        return [t for t in transfers if t["island"] == island]

    def get_transfer_by_id(self, transfer_id: str) -> dict:
        """Получить трансфер по ID"""
        transfers = self.data.get("transfers", [])
        for transfer in transfers:
            if transfer["id"] == transfer_id:
                return transfer
        return None


# Глобальный экземпляр (будет инициализирован с API в bot.py)
_data_loader_instance = None


def get_data_loader() -> DataLoader:
    """Получить экземпляр DataLoader"""
    if _data_loader_instance is None:
        raise RuntimeError("DataLoader не инициализирован! Вызовите set_data_loader() в bot.py")
    return _data_loader_instance


def set_data_loader(api: PelagosAPI):
    """Установить экземпляр DataLoader"""
    global _data_loader_instance
    _data_loader_instance = DataLoader(api=api)