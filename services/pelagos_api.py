import logging
from typing import Any, Dict, List, Optional

from .api_client import APIClient
from .schemas import Hotel, HotelRoom, Pagination, Region, RoomPrices, Service, ExcursionMonth, ExcursionEvent, Transfer

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

    # === ЭКСКУРСИИ ===

    async def get_group_tours_calendar(
        self,
        date: str = None,
        location: int = 0
    ) -> List[ExcursionMonth]:
        """
        Получить календарь групповых туров

        Args:
            date: дата в формате DD.MM.YYYY (опционально)
            location: ID локации (0 = все локации)

        Returns:
            список месяцев с экскурсиями
        """
        # ВАЖНО: Всегда используем /fixed/ для получения только групповых экскурсий
        if date:
            endpoint = f"group-tours/{date}/fixed/"
        else:
            # Fallback на /fixed/ если дата не указана (хотя лучше всегда передавать дату)
            endpoint = "group-tours/fixed/"

        params = {
            "calendar": 1,
            "location": location
        }

        data = await self.client.get(endpoint, params=params)

        if not data or data.get("code") != "OK":
            return []

        rv = data.get("rv", {})
        axis = rv.get("axis", [])

        months = []
        for month_data in axis:
            month = ExcursionMonth.from_dict(month_data)
            if month:
                months.append(month)

        return months

    async def get_excursion_event_details(self, event_id: int) -> Optional[ExcursionEvent]:
        """
        Получить детальную информацию об экскурсионном событии

        Args:
            event_id: ID события

        Returns:
            объект ExcursionEvent с полными данными или None
        """
        endpoint = f"group-tours-event/{event_id}/"
        params = {"extend": 1}

        data = await self.client.get(endpoint, params=params)

        if not data or data.get("code") != "OK":
            return None

        row = data.get("row")
        if not row:
            return None

        # Создаем ExcursionEvent из service данных
        # Поскольку это детальный запрос, нам нужно обернуть service в event структуру

        # Пробуем получить дату из rlst (список расписаний)
        sdt = 0
        rlst = row.get("rlst", [])
        if rlst and len(rlst) > 0:
            # Берем первое ближайшее расписание
            sdt = rlst[0].get("sdt", 0)

        event_data = {
            "id": event_id,
            "service_id": row.get("id"),
            "base_id": row.get("base_id", 1),
            "sdt": sdt,  # Получаем из rlst если есть
            "service": row
        }

        return ExcursionEvent.from_dict(event_data)

    async def get_excursions_by_location_and_date(
        self,
        location_code: str = None,
        date: str = None
    ) -> List[ExcursionEvent]:
        """
        Получить все экскурсии для конкретной локации и даты

        Args:
            location_code: код локации (например, 'cebu', 'bohol')
            date: дата в формате YYYY-MM-DD

        Returns:
            список ExcursionEvent
        """
        # Получаем ID локации по коду
        location_id = 0
        if location_code:
            # Маппинг кодов локаций на ID
            location_map = {
                "cebu": 9,
                "bohol": 10,
                "boracay": 8,
                "panglao": 10,
                # Добавьте другие локации по необходимости
            }
            location_id = location_map.get(location_code.lower(), 0)

        # Конвертируем дату из YYYY-MM-DD в DD.MM.YYYY если нужно
        api_date = None
        if date:
            from datetime import datetime
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                api_date = dt.strftime("%d.%m.%Y")
            except ValueError:
                logger.error(f"Неверный формат даты: {date}")
                return []

        months = await self.get_group_tours_calendar(date=api_date, location=location_id)

        if not months:
            return []

        # Собираем все события из календаря
        # Когда передается дата (например, 01.01.2026), API возвращает календарь месяца,
        # который может включать дни из соседних месяцев (other: true).
        # Мы собираем ВСЕ события, а фильтрация по дате происходит на уровне выше.
        all_events = []
        for month in months:
            for day in month.days:
                all_events.extend(day.events)

        return all_events

    async def get_private_excursions(
        self,
        location_id: int = 0,
        date: str = None
    ) -> List[dict]:
        """
        Получить индивидуальные экскурсии через list=1

        Args:
            location_id: ID локации (0 = все локации)
            date: дата в формате DD.MM.YYYY (опционально)

        Returns:
            список словарей с индивидуальными экскурсиями
        """
        endpoint = "group-tours/"
        if date:
            endpoint = f"group-tours/{date}/"

        params = {
            "list": 1,
            "location": location_id
        }

        logger.info(f"🌐 API Request: {endpoint} with params: {params}")
        data = await self.client.get(endpoint, params=params)
        logger.info(f"📥 API Response code: {data.get('code') if data else 'None'}, items: {len(data.get('lst', [])) if data else 0}")

        if not data or data.get("code") != "OK":
            return []

        lst = data.get("lst", [])

        # Фильтруем только индивидуальные экскурсии
        # group_ex == 0 или отсутствует (None) = индивидуальная
        # group_ex > 0 = групповая
        private_excursions = []
        for item in lst:
            group_ex = item.get("group_ex")
            # Если group_ex отсутствует (None) или равен 0 - это индивидуальная экскурсия
            if group_ex is None or group_ex == 0:
                private_excursions.append(item)

        return private_excursions

    async def get_companions_calendar(
        self,
        location_id: int = 0,
        date: str = None
    ) -> List[dict]:
        """
        Получить календарь с экскурсиями для поиска попутчиков (flex API)

        Args:
            location_id: ID локации (0 = все локации)
            date: начальная дата в формате DD.MM.YYYY (опционально)

        Returns:
            список дней с событиями (events)
        """
        # ВАЖНО: для поиска попутчиков нужен /flex/ в пути!
        endpoint = "group-tours/flex/"
        if date:
            endpoint = f"group-tours/{date}/flex/"

        params = {
            "calendar": 1,
            "location": location_id
        }

        # Формируем полный URL для логирования
        full_url = f"https://ru.pelagos.ru/{endpoint}?calendar={params['calendar']}&location={params['location']}"
        logger.info(f"🌐 Companions API Request: {full_url}")
        logger.info(f"📋 Params: {params}")

        data = await self.client.get(endpoint, params=params)
        logger.info(f"📥 Companions API Response code: {data.get('code') if data else 'None'}")

        if not data or data.get("code") != "OK":
            return []

        # ИСПРАВЛЕНО: Правильная структура ответа rv.axis[0].days
        rv = data.get("rv", {})
        axis = rv.get("axis", [])

        if not axis:
            logger.warning("⚠️ Нет данных в rv.axis")
            return []

        # Берем первый месяц из axis и возвращаем его дни
        first_month = axis[0]
        days = first_month.get("days", [])

        # Подсчитываем общее количество событий для отладки
        total_events = sum(len(day.get('events', [])) for day in days)
        logger.info(f"✅ Получено {len(days)} дней из календаря попутчиков")
        logger.info(f"📊 Всего событий в календаре: {total_events}")

        return days

    async def get_companion_event_details(self, event_id: int) -> Optional[dict]:
        """
        Получить детальную информацию о событии поиска попутчиков

        Args:
            event_id: ID события

        Returns:
            словарь с данными события или None
        """
        endpoint = f"group-tours-event/{event_id}/"
        params = {"extend": 1}

        logger.info(f"🌐 Event Details API Request: {endpoint}")
        data = await self.client.get(endpoint, params=params)

        if not data or data.get("code") != "OK":
            return None

        return data.get("row")

    # === ЦЕНЫ УСЛУГ (трансферы, экскурсии) ===

    async def get_service_prices(self, service_id: int) -> List[Dict[str, Any]]:
        """
        Получить цены услуги (трансфера, экскурсии и т.п.)

        Args:
            service_id: ID услуги

        Returns:
            Список ценников с plst (список цен для разного кол-ва людей)
        """
        endpoint = f"export-services-prices/{service_id}/"
        logger.info(f"🌐 API запрос цен услуги: {endpoint}")

        data = await self.client.get(endpoint)

        if not data or data.get("code") != "OK":
            logger.warning(f"⚠️ Не удалось получить цены для услуги {service_id}")
            return []

        prices = data.get("prices", [])
        logger.debug(f"📦 Получено {len(prices)} ценников для услуги {service_id}")

        return prices

    # === ТРАНСФЕРЫ ===

    async def get_transfers(
        self,
        location_id: int = None,
        perpage: int = 200,
        start: int = 0
    ) -> Dict[str, Any]:
        """
        Получить трансферы

        Args:
            location_id: ID локации для фильтрации (опционально)
            perpage: количество на странице
            start: с какого номера начинать

        Returns:
            dict с ключами: transfers, pagination
        """
        params = {
            "type": 1200,  # Тип трансфера (subtype из API)
            "perpage": perpage,
            "start": start
        }

        if location_id:
            params["location"] = location_id

        logger.info(f"🌐 API Request (Transfers): export-services/ with params: {params}")
        data = await self.client.get("export-services/", params=params)
        logger.info(f"📥 API Response code: {data.get('code') if data else 'None'}, transfers: {len(data.get('services', [])) if data else 0}")

        if not data or data.get("code") != "OK":
            return {"transfers": [], "pagination": None}

        transfers = []
        for transfer_data in data.get("services", []):
            transfer = Transfer.from_dict(transfer_data)
            if transfer:
                transfers.append(transfer)

        pagination_data = data.get("pages")
        pagination = Pagination.from_dict(pagination_data) if pagination_data else None

        return {"transfers": transfers, "pagination": pagination, "raw_data": data}

    async def get_all_transfers(
        self,
        location_id: int = None
    ) -> List[Transfer]:
        """
        Получить ВСЕ трансферы (автоматическая пагинация)

        Args:
            location_id: ID локации для фильтрации (опционально)

        Returns:
            список Transfer
        """
        all_transfers = []
        perpage = 200
        start = 0

        while True:
            result = await self.get_transfers(location_id=location_id, perpage=perpage, start=start)
            transfers = result["transfers"]

            if not transfers:
                break

            all_transfers.extend(transfers)

            # Проверяем, есть ли еще трансферы
            pagination = result["pagination"]
            if pagination and (start + perpage >= pagination.total):
                break

            start += perpage

        return all_transfers

    async def close(self):
        """Закрыть соединение"""
        await self.client.close()
