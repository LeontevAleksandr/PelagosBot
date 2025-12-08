"""Загрузчик данных из JSON (MVP)"""
import json
import os


class DataLoader:
    """Класс для работы с mock данными"""
    
    def __init__(self, json_path: str = "data/mock_data.json"):
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
    
    def get_hotels_by_filters(
        self, 
        island: str = None,
        stars: int = None,
        min_price: float = None,
        max_price: float = None
    ) -> list:
        """
        Получить отели по фильтрам
        
        Args:
            island: код острова
            stars: количество звезд
            min_price: минимальная цена
            max_price: максимальная цена
        """
        hotels = self.data.get("hotels", [])
        
        # Фильтр по острову
        if island:
            hotels = [h for h in hotels if h["island"] == island]
        
        # Фильтр по звездам
        if stars:
            hotels = [h for h in hotels if h["stars"] == stars]
        
        # Фильтр по цене (проверяем, что самый дешевый номер не превышает max_price на 30%)
        if min_price is not None and max_price is not None:
            filtered = []
            max_allowed_price = max_price * 1.3  # +30% от максимальной цены

            for hotel in hotels:
                rooms = hotel.get("rooms", [])
                if rooms:
                    # Находим самый дешевый номер
                    cheapest_room_price = min(room["price"] for room in rooms)
                    # Проверяем, что самый дешевый номер не дороже max_price + 30%
                    if cheapest_room_price <= max_allowed_price:
                        filtered.append(hotel)
            hotels = filtered
        
        return hotels
    
    def get_hotel_by_id(self, hotel_id: str) -> dict:
        """Получить отель по ID"""
        hotels = self.data.get("hotels", [])
        for hotel in hotels:
            if hotel["id"] == hotel_id:
                return hotel
        return None
    
    def get_room_by_id(self, hotel_id: str, room_id: str) -> dict:
        """Получить комнату по ID"""
        hotel = self.get_hotel_by_id(hotel_id)
        if not hotel:
            return None

        for room in hotel.get("rooms", []):
            if room["id"] == room_id:
                return room
        return None

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


# Глобальный экземпляр
data_loader = DataLoader()