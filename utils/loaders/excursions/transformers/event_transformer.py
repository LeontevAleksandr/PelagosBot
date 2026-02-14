"""Трансформер для групповых экскурсий (event)"""
import logging
from typing import Optional
from datetime import datetime
from services.schemas import ExcursionEvent
from .base import BaseTransformer

logger = logging.getLogger(__name__)


class EventTransformer(BaseTransformer):
    """Трансформер для преобразования ExcursionEvent в словарь"""

    @classmethod
    def transform(cls, event: ExcursionEvent, excursion_type: str = "group") -> Optional[dict]:
        """
        Преобразовать ExcursionEvent в dict для обработчиков (групповые экскурсии)

        Args:
            event: Объект события экскурсии
            excursion_type: Тип экскурсии (по умолчанию "group")

        Returns:
            Словарь с данными экскурсии или None
        """
        if not event or not event.service:
            return None

        service = event.service

        # Фильтруем услуги только для агентов
        agents_only = getattr(service, 'agents_only', None)
        if agents_only is not None and agents_only > 0:
            logger.debug(f"⏭️ Пропускаем экскурсию {service.name} (agents_only={agents_only})")
            return None

        # Дата и время
        date_str = None
        time_str = None
        if event.sdt:
            try:
                dt = datetime.fromtimestamp(event.sdt)
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            except Exception as e:
                logger.error(f"Ошибка конвертации timestamp {event.sdt}: {e}")

        # Остров
        location = getattr(service, 'location', 9)
        island, island_name = cls.resolve_island_location(location)

        # Фото
        # Сначала пробуем взять массив pics (как у индивидуальных),
        # и только потом fallback на единичное pic
        pics = getattr(service, 'pics', None)
        pic = getattr(service, 'pic', None)

        logger.debug(f"Group excursion event {event.id}, service {event.service_id}: pics = {pics}, pic = {pic}")

        # Если есть массив pics - берём первую фотографию
        if pics and len(pics) > 0:
            photo_url = cls.build_photo_url(pics[0])
        # Иначе пробуем единичное pic
        elif pic:
            photo_url = cls.build_photo_url(pic)
        else:
            photo_url = None

        # Описание
        html = getattr(service, 'html', '')
        description = cls.clean_html(html)[:200] if html else ""

        # Цена: используем min_price из service (минимальная цена для максимальной группы)
        # Приоритет: min_price > current.price > event.price
        price = 0

        # Сначала проверяем min_price - это правильная минимальная цена
        min_price = getattr(service, 'min_price', None)
        if min_price and min_price > 0:
            price = min_price
            logger.debug(f"Цена из min_price: ${price} для '{service.name}'")

        # Если нет min_price, берём из current (но это может быть цена для конкретной группы)
        if not price:
            current = getattr(service, 'current', None)
            if current and isinstance(current, dict):
                price = current.get('price', 0)
                grp = current.get('grp', 0)
                logger.debug(f"Цена из current: ${price} для {grp} чел. ('{service.name}')")

        # В крайнем случае - event.price
        if not price:
            price = event.price or 0
            if price:
                logger.debug(f"Цена из event.price: ${price} для '{service.name}'")

        # Получаем max_price если есть (для отображения диапазона)
        max_price = getattr(service, 'max_price', None)

        # Извлекаем price_list из rlst (список цен для разного количества людей)
        rlst = getattr(service, 'rlst', None)
        price_list = {}
        if rlst:
            price_list = cls.extract_price_list(rlst)
            logger.debug(f"Price list для '{service.name}': {price_list}")

        return {
            "id": str(event.id),
            "service_id": str(event.service_id),
            "name": service.name,
            "island": island,
            "island_name": island_name,
            "type": excursion_type,
            "date": date_str,
            "time": time_str,
            "duration": event.duration // 60 if event.duration else None,
            "description": description,
            "full_description": html,
            "price": price,
            "price_usd": price,
            "min_price": price,  # Минимальная цена (для максимальной группы)
            "max_price": max_price,  # Максимальная цена (для 1 человека)
            "price_list": price_list,  # Список цен для разного количества людей
            "people_count": event.pax,
            "companions_count": event.pax,
            "photo": photo_url,
            "url": f"https://ru.pelagos.ru/group-tours-event/{event.id}/",
            "has_russian_guide": getattr(service, 'russian_guide', 0) == 10,
        }
