"""Трансформер для ежедневных экскурсий (daily service)"""
from typing import Optional
from .base import BaseTransformer


class DailyTransformer(BaseTransformer):
    """Трансформер для преобразования ежедневных экскурсий в словарь"""

    @classmethod
    def transform(cls, service_data: dict) -> Optional[dict]:
        """
        Преобразовать ежедневную экскурсию (daily service) в dict

        Args:
            service_data: Данные сервиса из API

        Returns:
            Словарь с данными экскурсии или None
        """
        if not service_data:
            return None

        # API уже вернул ежедневные через props=daily, дополнительная проверка не нужна

        # Остров
        location = service_data.get('location', 9)
        island, island_name = cls.resolve_island_location(location)

        # Фото
        pics = service_data.get('pics', [])
        photo_url = cls.build_photo_url(pics[0]) if pics else None

        # Описание
        html = service_data.get('html', '')
        description = cls.clean_html(html)

        # Цены - для ежедневных используем min_price как базу
        min_price = service_data.get('min_price', 0)
        max_price = service_data.get('max_price', 0)
        price_list = cls.extract_price_list(service_data.get('rlst', []))

        excursion_id = service_data.get('id')

        # Определяем это групповая или индивидуальная ежедневная
        group_ex = service_data.get('group_ex')
        is_group_daily = group_ex == 10

        return {
            "id": str(excursion_id),
            "service_id": str(excursion_id),
            "name": service_data.get('name', ''),
            "island": island,
            "island_name": island_name,
            "location_id": location,
            "type": "private",  # Показываем в индивидуальных
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
            "url": service_data.get('inhttp') or f"https://ru.pelagos.ru/activity/{excursion_id}/",
            "has_russian_guide": service_data.get('russian_guide') == 10,
            "private_transport": service_data.get('private_transport') == 10,
            "lunch_included": service_data.get('lunch_included') == 10,
            "tickets_included": service_data.get('tickets_included') == 10,
            "is_daily": True,
            "is_group_daily": is_group_daily,
            "ord": service_data.get('ord', 0),
        }
