"""Менеджер для работы с медиа-файлами"""
import os
from aiogram.types import FSInputFile, URLInputFile


class MediaManager:
    """
    Класс для загрузки фотографий.
    Легко заменить на загрузку из БД в будущем.
    """
    
    def __init__(self, local_media_dir: str = "data/media"):
        self.local_media_dir = local_media_dir
        
        # Создаем папку если её нет
        os.makedirs(local_media_dir, exist_ok=True)
    
    async def get_photo(self, photo_path: str):
        """
        Получить фото для отправки в Telegram.
        
        Args:
            photo_path: путь к фото (может быть URL или локальный путь)
        
        Returns:
            FSInputFile или URLInputFile или None
        """
        if not photo_path:
            return None
        
        # Если это URL
        if photo_path.startswith(('http://', 'https://')):
            return URLInputFile(photo_path)
        
        # Если это локальный файл
        full_path = os.path.join(self.local_media_dir, photo_path)
        
        if os.path.exists(full_path):
            return FSInputFile(full_path)
        
        return None
    
    def has_photo(self, photo_path: str) -> bool:
        """Проверить наличие фото"""
        if not photo_path:
            return False
        
        # URL всегда доступны (предполагаем)
        if photo_path.startswith(('http://', 'https://')):
            return True
        
        # Проверяем локальный файл
        full_path = os.path.join(self.local_media_dir, photo_path)
        return os.path.exists(full_path)


# Глобальный экземпляр
media_manager = MediaManager()


# ========== Функции для будущей замены на БД ==========

async def get_hotel_photo(hotel_id: str, location_code: str = None):
    """
    Получить фото отеля.
    В будущем заменить на запрос к БД.

    Args:
        hotel_id: ID отеля
        location_code: код локации для оптимизации поиска (опционально)
    """
    from utils.data_loader import get_data_loader

    hotel = await get_data_loader().get_hotel_by_id(int(hotel_id), location_code=location_code)
    if not hotel:
        return None

    photo_path = hotel.get("photo")
    return await media_manager.get_photo(photo_path)


async def get_excursion_photo(excursion_id: str):
    """
    Получить фото экскурсии.
    В будущем заменить на запрос к БД.
    """
    from utils.data_loader import get_data_loader

    excursion = await get_data_loader().get_excursion_by_id(excursion_id)
    if not excursion:
        return None

    photo_path = excursion.get("photo")
    return await media_manager.get_photo(photo_path)


async def get_transfer_photo(transfer_id: str):
    """
    Получить фото трансфера.
    В будущем заменить на запрос к БД.
    """
    from utils.data_loader import get_data_loader

    transfer = await get_data_loader().get_transfer_by_id(transfer_id)
    if not transfer:
        return None

    photo_path = transfer.get("photo")
    return await media_manager.get_photo(photo_path)