"""Загрузчик данных из JSON (MVP) и адаптер для Pelagos API"""
import json
import os
import logging
from typing import Optional, List
from services.pelagos_api import PelagosAPI
from services.schemas import Hotel, HotelRoom

logger = logging.getLogger(__name__)


class DataLoader:
    """Класс для работы с mock данными и Pelagos API"""

    def __init__(self, api: Optional[PelagosAPI] = None, json_path: str = "data/mock_data.json"):
        self.api = api
        self.json_path = json_path
        self.data = self._load_data()

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
        load_first_only: bool = True
    ) -> dict:
        """
        Получить отели по фильтрам (из Pelagos API)

        Args:
            island: код острова
            stars: количество звезд
            min_price: минимальная цена
            max_price: максимальная цена
            load_first_only: загрузить только первый отель с номерами (для быстрого отображения)

        Returns:
            dict: {
                'hotels': list - список отелей (первый - с номерами, остальные - без),
                'total': int - общее количество отелей
            }
        """
        logger.info(f"🔍 get_hotels_by_filters: island={island}, stars={stars}, load_first_only={load_first_only}")

        if not self.api or not island:
            logger.warning(f"⚠️ Нет API или острова")
            return {'hotels': [], 'total': 0}

        # Получаем отели из API (только метаданные, без номеров)
        logger.info(f"📡 Запрос отелей для {island}...")
        hotels = await self.api.get_all_hotels(island)
        logger.info(f"✅ Получено {len(hotels)} отелей")

        # Фильтр по звездам
        if stars:
            hotels = [h for h in hotels if h.stars == stars]
            logger.info(f"⭐ После фильтра по звездам ({stars}): {len(hotels)} отелей")

        total_hotels = len(hotels)

        if not hotels:
            return {'hotels': [], 'total': 0}

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
                return {'hotels': [], 'total': 0}

            # Остальные отели - без номеров (загрузим позже по запросу)
            for hotel in hotels[1:]:
                result.append(self._convert_hotel(hotel, []))

        else:
            # Загружаем все отели с номерами (старый способ)
            logger.info(f"⏳ Полная загрузка: получаем номера для всех {len(hotels)} отелей...")
            for i, hotel in enumerate(hotels):
                try:
                    rooms = await self.api.get_all_rooms(hotel.id)
                    result.append(self._convert_hotel(hotel, rooms))
                    if (i + 1) % 5 == 0:
                        logger.info(f"   📊 Обработано {i+1}/{len(hotels)}")
                except Exception as e:
                    logger.error(f"   ❌ Ошибка для отеля {hotel.id}: {e}")
                    continue

        logger.info(f"✅ Возвращаем {len(result)} отелей (total={total_hotels})")
        return {'hotels': result, 'total': total_hotels}

    async def get_hotel_by_id(self, hotel_id: int, location_code: str = None) -> Optional[dict]:
        """
        Получить отель по ID (из Pelagos API)

        Args:
            hotel_id: ID отеля
            location_code: код локации для оптимизации поиска
        """
        if not self.api:
            return None

        try:
            # Если есть локация - ищем там, иначе используем общий поиск
            if location_code:
                # Получаем отели из конкретной локации
                hotels_result = await self.api.get_hotels(location_code, perpage=100, start=0)
                hotels = hotels_result.get('hotels', [])

                # Ищем нужный отель
                hotel = None
                for h in hotels:
                    if h.id == hotel_id:
                        hotel = h
                        break

                if not hotel:
                    logger.warning(f"⚠️ Отель {hotel_id} не найден в локации {location_code}")
                    return None
            else:
                # Старый способ - поиск по всем регионам (медленно)
                hotel = await self.api.get_hotel_by_id(hotel_id)
                if not hotel:
                    return None

            # Загружаем номера
            rooms = await self.api.get_all_rooms(hotel_id)
            return self._convert_hotel(hotel, rooms)

        except Exception as e:
            logger.error(f"❌ Ошибка get_hotel_by_id({hotel_id}): {e}")
            return None

    async def get_room_by_id(self, hotel_id: int, room_id: int) -> Optional[dict]:
        """Получить номер по ID (из Pelagos API)"""
        if not self.api:
            return None

        rooms = await self.api.get_all_rooms(hotel_id)
        for room in rooms:
            if room.id == room_id:
                return self._convert_room(room)

        return None

    def _convert_hotel(self, hotel: Hotel, rooms: List[HotelRoom]) -> dict:
        """Преобразовать Hotel в dict для обработчика"""
        return {
            'id': str(hotel.id),
            'name': hotel.name,
            'stars': hotel.stars or 0,
            'island_name': hotel.address or 'Не указан',
            'room_type': 'Стандарт',
            'rooms': [self._convert_room(r) for r in rooms]
        }

    def _convert_room(self, room: HotelRoom) -> dict:
        """Преобразовать HotelRoom в dict для обработчика"""
        return {
            'id': str(room.id),
            'name': room.name,
            'price': 100  # TODO: получить реальную цену через api.get_room_prices(room.id)
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