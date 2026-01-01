"""Загрузчик данных для трансферов"""
import logging
from typing import Optional
from services.pelagos_api import PelagosAPI
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class TransfersLoader:
    """Класс для работы с трансферами через Pelagos API"""

    # TTL для кэша (3 часа)
    CACHE_TTL = 10800

    # Маппинг кодов островов на ID локаций в API
    LOCATION_MAP = {
        "cebu": 9,
        "bohol": 10,
        "boracay": 8,
        "panglao": 10,
        "palawan": 11,
        "manila": 7,
        # Добавьте другие острова по необходимости
    }

    def __init__(self, api: Optional[PelagosAPI] = None, json_path: str = None):
        """
        Args:
            api: API для работы с трансферами (Pelagos API)
            json_path: устаревший параметр, оставлен для обратной совместимости
        """
        self.api = api
        self.cache = get_cache_manager()

    async def get_transfers_by_island(self, island: str = None) -> list:
        """
        Получить трансферы по острову

        Args:
            island: код острова (например, 'cebu', 'bohol', None - все трансферы)

        Returns:
            list: список словарей с информацией о трансферах
        """
        if not self.api:
            logger.warning("⚠️ API не инициализирован")
            return []

        # Получаем ID локации по коду острова
        location_id = None
        if island:
            location_id = self.LOCATION_MAP.get(island.lower())
            if location_id is None:
                logger.warning(f"⚠️ Неизвестный код острова: {island}")
                return []

        # Создаем ключ кэша
        cache_key = f"transfers:{island if island else 'all'}"
        cached_transfers = self.cache.get(cache_key)

        if cached_transfers:
            logger.info(f"✓ Используем кэш трансферов для {island or 'всех островов'} ({len(cached_transfers)} шт)")
            return cached_transfers

        try:
            if location_id:
                logger.info(f"📡 Запрос трансферов для {island} (location_id={location_id})...")
            else:
                logger.info(f"📡 Запрос всех трансферов (без фильтра по location)...")

            # Получаем все трансферы через API
            transfers_objects = await self.api.get_all_transfers(location_id=location_id)

            # Конвертируем Transfer объекты в словари для совместимости
            transfers = []
            for transfer in transfers_objects:
                # Формируем описание на основе характеристик трансфера
                description_parts = []
                if transfer.group_ex:
                    description_parts.append("Групповой трансфер")
                elif transfer.private_transport:
                    description_parts.append("Приватный трансфер")
                else:
                    description_parts.append("Комфортабельный трансфер")

                if transfer.russian_guide:
                    description_parts.append("с русскоговорящим гидом")

                description = ". ".join(description_parts) + "."

                transfer_dict = {
                    'id': str(transfer.id),
                    'name': transfer.name,
                    'island': island or 'unknown',
                    'location': transfer.location,
                    'base_id': transfer.base_id,
                    'type': transfer.type,
                    'subtype': transfer.subtype,
                    'russian_guide': transfer.russian_guide,
                    'private_transport': transfer.private_transport,
                    'group_ex': transfer.group_ex,
                    'pics': transfer.pics,
                    'inhttp': transfer.inhttp,
                    'ord': transfer.ord,
                    'score': transfer.score,
                    # Добавляем недостающие поля для совместимости
                    'description': description,
                    'price_per_person_usd': 25,  # Дефолтная цена, т.к. в API нет прямых цен для трансферов
                    'base_price_usd': 25
                }

                # Извлекаем URL первого фото, если есть
                if transfer.pics and len(transfer.pics) > 0:
                    first_pic = transfer.pics[0]
                    # Используем формат md5 как у экскурсий и отелей
                    if isinstance(first_pic, dict) and 'md5' in first_pic and 'ext' in first_pic:
                        photo_url = f"https://app.pelagos.ru/pic/{first_pic['md5']}/{first_pic['md5']}.{first_pic['ext']}"
                        transfer_dict['photo'] = photo_url

                transfers.append(transfer_dict)

            # Сортируем по ord (рейтингу) в порядке убывания
            transfers = sorted(transfers, key=lambda t: t.get('ord', 0), reverse=True)

            # Кэшируем результат
            self.cache.set(cache_key, transfers, ttl=self.CACHE_TTL)

            logger.info(f"✅ Загружено {len(transfers)} трансферов из API")
            return transfers

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки трансферов: {e}")
            return []

    async def get_transfer_by_id(self, transfer_id: str) -> Optional[dict]:
        """
        Получить трансфер по ID

        Args:
            transfer_id: ID трансфера

        Returns:
            dict: словарь с информацией о трансфере или None
        """
        if not self.api:
            logger.warning("⚠️ API не инициализирован")
            return None

        try:
            # Пытаемся найти в кэше среди всех трансферов
            for island_key in ['cebu', 'bohol', 'boracay', 'panglao', 'palawan', 'all']:
                cache_key = f"transfers:{island_key}"
                cached_transfers = self.cache.get(cache_key)

                if cached_transfers:
                    for transfer in cached_transfers:
                        if str(transfer['id']) == str(transfer_id):
                            logger.info(f"✓ Трансфер {transfer_id} найден в кэше")
                            return transfer

            # Если не нашли в кэше, загружаем все трансферы
            logger.info(f"📡 Трансфер {transfer_id} не найден в кэше, загружаем все...")
            all_transfers = await self.get_transfers_by_island(island=None)

            # Ищем нужный трансфер
            for transfer in all_transfers:
                if str(transfer['id']) == str(transfer_id):
                    return transfer

            logger.warning(f"⚠️ Трансфер с ID {transfer_id} не найден")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения трансфера {transfer_id}: {e}")
            return None
