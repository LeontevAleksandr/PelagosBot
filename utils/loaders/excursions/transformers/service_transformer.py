"""Трансформер для индивидуальных экскурсий (service)"""
from typing import Optional
from .base import BaseTransformer


class ServiceTransformer(BaseTransformer):
    """Трансформер для преобразования service данных в словарь"""

    @classmethod
    def transform(cls, service_data: dict, excursion_type: str = "private") -> Optional[dict]:
        """
        Преобразовать service из list API в dict для обработчиков (индивидуальные экскурсии)

        Args:
            service_data: Данные сервиса из API
            excursion_type: Тип экскурсии (по умолчанию "private")

        Returns:
            Словарь с данными экскурсии или None
        """
        if not service_data:
            return None

        # Остров
        location = service_data.get('location', 9)
        island, island_name = cls.resolve_island_location(location)

        # Фото
        pics = service_data.get('pics', [])
        photo_url = cls.build_photo_url(pics[0]) if pics else None

        # Описание
        html = service_data.get('html', '')
        description = cls.clean_html(html)

        # Цены
        min_price = service_data.get('min_price', 0)
        max_price = service_data.get('max_price', 0)
        price_list = cls.extract_price_list(service_data.get('rlst', []))

        excursion_id = service_data.get('id')

        # Проверяем, является ли это ежедневной экскурсией
        is_daily = service_data.get('daily') == 10

        return {
            "id": str(excursion_id),
            "service_id": str(excursion_id),
            "name": service_data.get('name', ''),
            "island": island,
            "island_name": island_name,
            "location_id": location,
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
            "url": service_data.get('inhttp') or (f"https://ru.pelagos.ru/activity/{excursion_id}/" if excursion_id else ""),
            "has_russian_guide": service_data.get('russian_guide') == 10,
            "private_transport": service_data.get('private_transport') == 10,
            "lunch_included": service_data.get('lunch_included') == 10,
            "tickets_included": service_data.get('tickets_included') == 10,
            "is_daily": is_daily,
        }
