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
        
        # Фильтр по цене (ищем хотя бы один номер в диапазоне)
        if min_price is not None and max_price is not None:
            filtered = []
            for hotel in hotels:
                has_room_in_range = any(
                    min_price <= room["price"] <= max_price
                    for room in hotel.get("rooms", [])
                )
                if has_room_in_range:
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
    
    def filter_rooms_by_price(self, rooms: list, min_price: float, max_price: float) -> list:
        """Отфильтровать комнаты по цене"""
        return [
            room for room in rooms
            if min_price <= room["price"] <= max_price
        ]


# Глобальный экземпляр
data_loader = DataLoader()