"""Базовый трансформер с общими методами для преобразования данных экскурсий"""
import logging
from typing import Optional, Dict
from ..constants import LOCATION_MAP, ISLAND_NAMES, PRIVATE_ISLANDS_MAP

logger = logging.getLogger(__name__)


class BaseTransformer:
    """Базовый класс с общими методами для трансформации данных экскурсий"""

    @staticmethod
    def get_island_info(location_id: int) -> tuple:
        """
        Получить код острова и название по location ID

        Args:
            location_id: ID локации

        Returns:
            tuple: (код острова, русское название)
        """
        for code, lid in LOCATION_MAP.items():
            if lid == location_id:
                return code, ISLAND_NAMES.get(code, code.capitalize())
        return "cebu", "Себу"

    @staticmethod
    def clean_html(html: str) -> str:
        """
        Очистить HTML от тегов и лишних пробелов

        Args:
            html: HTML строка

        Returns:
            Очищенный текст
        """
        if not html:
            return ""
        import re
        clean = re.sub('<.*?>', '', html)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    @staticmethod
    def build_photo_url(pic: dict) -> Optional[str]:
        """
        Построить URL фото из объекта pic

        Args:
            pic: Словарь с данными фото (md5, ext)

        Returns:
            URL фото или None
        """
        if not pic or not isinstance(pic, dict):
            logger.debug(f"Photo pic is empty or not dict: {pic}")
            return None
        md5 = pic.get('md5')
        ext = pic.get('ext')
        if md5 and ext:
            photo_url = f"https://ru.pelagos.ru/pic/{md5}/{md5}.{ext}"
            logger.debug(f"Built photo URL: {photo_url}")
            return photo_url
        else:
            logger.debug(f"Missing md5 or ext in pic: md5={md5}, ext={ext}")
            return None

    @staticmethod
    def extract_price_list(rlst: list) -> Dict[int, float]:
        """
        Извлечь список цен для разного количества человек из rlst

        Args:
            rlst: Список с данными о ценах

        Returns:
            Словарь {количество человек: цена}
        """
        price_list = {}
        if rlst and len(rlst) > 0:
            clst = rlst[0].get('clst', [])
            for item in clst:
                grp = item.get('grp')
                price = item.get('price')
                if grp and price:
                    price_list[grp] = price
        return price_list

    @staticmethod
    def resolve_island_location(location: int) -> tuple:
        """
        Разрешить location ID в код острова и название

        Использует новый PRIVATE_ISLANDS_MAP с fallback на старый маппинг

        Args:
            location: location ID

        Returns:
            tuple: (код острова, русское название острова)
        """
        if location in PRIVATE_ISLANDS_MAP:
            island_name = PRIVATE_ISLANDS_MAP[location]
            # Обратный маппинг для получения кода острова (для обратной совместимости)
            island_code_map = {v: k for k, v in LOCATION_MAP.items()}
            island = island_code_map.get(location, "cebu")
            return island, island_name
        else:
            # Fallback на старый метод если location не найден в новом маппинге
            return BaseTransformer.get_island_info(location)
