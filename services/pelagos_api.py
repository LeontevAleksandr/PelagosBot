import logging
from typing import Any, Dict, List, Optional

from .api_client import APIClient
from .schemas import Hotel, HotelRoom, Pagination, Region, RoomPrices, Service

logger = logging.getLogger(__name__)


class PelagosAPI:
    """Сервис для работы с API Pelagos"""

    def __init__(self, api_key: str = None):
        self.client = APIClient(
            base_url="https://app.pelagos.ru", api_key=api_key, timeout=30
        )

    # === РЕГИОНЫ ===

    async def get_regions(self) -> List[Region]:
        """Получить все регионы"""
        data = await self.client.get("export-locations/")

        if not data or data.get("code") != "OK":
            return []

        regions = []
        for region_data in data.get("locations", []):
            region = Region.from_dict(region_data)
            if region:
                regions.append(region)

        return regions

    async def get_region_by_code(self, code: str) -> Optional[Region]:
        """Найти регион по коду"""
        regions = await self.get_regions()
        for region in regions:
            if region.code == code:
                return region
        return None

    async def get_root_regions(self) -> List[Region]:
        """Получить только корневые регионы (без родителей)"""
        regions = await self.get_regions()
        return [r for r in regions if r.is_root]

    # === ОТЕЛИ ===

    async def get_hotels(
        self, location_code: str, perpage: int = 20, start: int = 0
    ) -> Dict[str, Any]:
        """
        Получить отели региона с пагинацией

        Returns:
            dict с ключами: hotels, pagination
        """
        endpoint = f"export-hotels/{location_code}/"
        params = {"perpage": perpage, "start": start}

        data = await self.client.get(endpoint, params=params)

        if not data or data.get("code") != "OK":
            return {"hotels": [], "pagination": None}

        hotels = []
        for hotel_data in data.get("hotels", []):
            hotel = Hotel.from_dict(hotel_data)
            if hotel:
                hotels.append(hotel)

        pagination_data = data.get("pages")
        pagination = Pagination.from_dict(pagination_data) if pagination_data else None

        return {"hotels": hotels, "pagination": pagination, "raw_data": data}

    async def get_all_hotels(self, location_code: str) -> List[Hotel]:
        """Получить ВСЕ отели региона (автоматическая пагинация)"""
        all_hotels = []
        perpage = 50
        start = 0

        while True:
            result = await self.get_hotels(location_code, perpage, start)
            hotels = result["hotels"]

            if not hotels:
                break

            all_hotels.extend(hotels)

            # Проверяем, есть ли еще отели
            pagination = result["pagination"]
            if pagination and (start + perpage >= pagination.total):
                break

            start += perpage

        return all_hotels


    # === НОМЕРА В ОТЕЛЕ ===

    async def get_rooms(
        self, hotel_id: int, perpage: int = 20, start: int = 0
    ) -> Dict[str, Any]:
        """
        Получить номера в отеле с пагинацией

        Args:
            hotel_id: ID отеля
            perpage: количество на странице
            start: с какого номера начинать

        Returns:
            dict с ключами: rooms, pagination
        """
        endpoint = f"export-hotels-rooms/{hotel_id}/"
        params = {"perpage": perpage, "start": start}

        data = await self.client.get(endpoint, params=params)

        if not data or data.get("code") != "OK":
            return {"rooms": [], "pagination": None}

        rooms = []
        for room_data in data.get("rooms", []):
            room = HotelRoom.from_dict(room_data)
            if room:
                rooms.append(room)

        pagination_data = data.get("pages")
        pagination = Pagination.from_dict(pagination_data) if pagination_data else None

        return {"rooms": rooms, "pagination": pagination, "raw_data": data}

    # === УСЛУГИ ===

    async def get_services(
        self,
        perpage: int = 20,
        start: int = 0,
        service_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Получить услуги"""
        params = {"perpage": perpage, "start": start}

        if service_id:
            params["id"] = service_id
        if search:
            params["search"] = search

        data = await self.client.get("export-services/", params=params)

        if not data or data.get("code") != "OK":
            return {"services": [], "pagination": None}

        services = []
        for service_data in data.get("services", []):
            service = Service.from_dict(service_data)
            if service:
                services.append(service)

        pagination_data = data.get("pages")
        pagination = Pagination.from_dict(pagination_data) if pagination_data else None

        return {"services": services, "pagination": pagination, "raw_data": data}

    # === ЦЕНЫ НОМЕРОВ ===

    async def get_room_prices(self, room_id: int) -> List[RoomPrices]:
        """Получить цены номера"""
        endpoint = f"export-hotels-rooms-prices/{room_id}/"
        full_url = f"{self.client.base_url}/{endpoint}"

        logger.info(f"🌐 API запрос цен: {full_url}")

        data = await self.client.get(endpoint)

        result = data.get("prices") or []

        logger.debug(f"📦 Ответ API для номера {room_id}: {len(result)} ценников")
        if logger.isEnabledFor(logging.DEBUG):
            import json
            logger.debug(f"📄 Полное тело ответа:\n{json.dumps(data, indent=2, ensure_ascii=False)}")

        return result

    # === ПОИСК ===

    async def search_hotels(self, query: str, limit: int = 10, regions_limit: int = 3) -> List[Hotel]:
        """
        Поиск отелей по названию

        Args:
            query: поисковый запрос
            limit: максимальное количество результатов
            regions_limit: количество регионов для поиска (по умолчанию 3)

        Returns:
            список найденных отелей
        """
        results = []
        all_regions = await self.get_regions()
        # Используем только регионы с родителями (не корневые)
        child_regions = [r for r in all_regions if r.parent and r.parent != 0][:regions_limit]

        for region in child_regions:
            hotels = await self.get_all_hotels(region.code)
            for hotel in hotels:
                if query.lower() in hotel.name.lower():
                    results.append(hotel)
                    if len(results) >= limit:
                        return results

        return results

    async def search_services(self, query: str, limit: int = 10) -> List[Service]:
        """Поиск услуг"""
        result = await self.get_services(search=query, perpage=limit)
        return result.get("services", [])[:limit]

    # === УТИЛИТЫ ===

    async def get_all_rooms(self, hotel_id: int) -> List[HotelRoom]:
        """Получить ВСЕ номера отеля (автоматическая пагинация)"""
        all_rooms = []
        perpage = 50
        start = 0
        max_iterations = 10  # Защита: максимум 500 номеров (10 * 50)

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            result = await self.get_rooms(hotel_id, perpage, start)
            rooms = result["rooms"]

            if not rooms:
                break

            all_rooms.extend(rooms)

            # Проверяем, есть ли еще номера
            pagination = result["pagination"]
            if not pagination:
                break

            if start + perpage >= pagination.total:
                break

            start += perpage

        if iteration >= max_iterations:
            logger.warning(
                f"⚠️ get_all_rooms({hotel_id}): достигнут лимит итераций ({max_iterations}), загружено {len(all_rooms)} номеров"
            )

        return all_rooms

    async def get_all_services(self, search: Optional[str] = None) -> List[Service]:
        """Получить ВСЕ услуги (автоматическая пагинация)"""
        all_services = []
        perpage = 50
        start = 0

        while True:
            params = {"perpage": perpage, "start": start}
            if search:
                params["search"] = search

            result = await self.get_services(**params)
            services = result["services"]

            if not services:
                break

            all_services.extend(services)

            # Проверяем, есть ли еще услуги
            pagination = result["pagination"]
            if pagination and (start + perpage >= pagination.total):
                break

            start += perpage

        return all_services

    async def close(self):
        """Закрыть соединение"""
        await self.client.close()
