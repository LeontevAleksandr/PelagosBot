"""Трансформер для экскурсий с попутчиками (companion event)"""
import logging
from typing import Optional
from datetime import datetime
from .base import BaseTransformer

logger = logging.getLogger(__name__)


class CompanionTransformer(BaseTransformer):
    """Трансформер для преобразования companion event в словарь"""

    @classmethod
    def transform(cls, event_data: dict, day_data: dict) -> Optional[dict]:
        """
        Преобразовать event из flex API (попутчики) в dict

        Args:
            event_data: Данные события
            day_data: Данные дня (дата, месяц, год)

        Returns:
            Словарь с данными экскурсии или None
        """
        if not event_data or not day_data:
            return None

        service = event_data.get('service', {})
        if not service:
            return None

        # Фильтруем услуги только для агентов
        agents_only = service.get('agents_only')
        if agents_only is not None and agents_only > 0:
            logger.debug(f"⏭️ Пропускаем экскурсию {service.get('name')} (agents_only={agents_only})")
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
        island, island_name = cls.resolve_island_location(location)

        # Фото
        photo_url = cls.build_photo_url(service.get('pic'))

        # Описание
        html = service.get('html', '')
        description = cls.clean_html(html)

        event_id = event_data.get('id')
        service_id = service.get('id')

        # Список попутчиков (может отсутствовать в кратком списке)
        companions_list = event_data.get('slst', [])

        # Подсчитываем ОБЩЕЕ количество людей из slst
        total_pax = sum(companion.get('pax', 0) for companion in companions_list)
        logger.debug(f"📊 Попутчики (краткий список) для {service.get('name')}: {len(companions_list)} записей, {total_pax} человек")

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
            "pax": total_pax,
            "companions": companions_list,
            "has_russian_guide": service.get('russian_guide') == 10,
            "private_transport": service.get('private_transport') == 10,
            "lunch_included": service.get('lunch_included') == 10,
            "tickets_included": service.get('tickets_included') == 10,
        }
