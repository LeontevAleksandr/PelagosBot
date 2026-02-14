"""Загрузчик данных для бота: фасад для работы со всеми типами данных"""
import logging
from typing import Optional
from services.pelagos_api import PelagosAPI
from utils.loaders import HotelsLoader, TransfersLoader, PackagesLoader
from utils.loaders.excursions import ExcursionsLoader

logger = logging.getLogger(__name__)


class DataLoader:
    """Фасад для работы с различными типами данных бота"""

    def __init__(self, api: Optional[PelagosAPI] = None, json_path: str = "data/mock_data.json"):
        """
        Args:
            api: API для работы с отелями, экскурсиями и трансферами (Pelagos API)
            json_path: путь к JSON файлу для пакетов
        """
        # Инициализируем специализированные загрузчики
        self.hotels_loader = HotelsLoader(api=api)
        self.excursions_loader = ExcursionsLoader(api=api)
        self.transfers_loader = TransfersLoader(api=api)  # Теперь использует API
        self.packages_loader = PackagesLoader(json_path=json_path)

    # ========== ОТЕЛИ (делегирование в HotelsLoader) ==========

    async def get_hotels_by_filters(
        self,
        island: str = None,
        stars: int = None,
        min_price: float = None,
        max_price: float = None,
        page: int = 0,
        per_page: int = None,
        check_in: str = None,
        check_out: str = None,
        filtered_hotels: list = None
    ) -> dict:
        """Получить отели по фильтрам"""
        return await self.hotels_loader.get_hotels_by_filters(
            island=island,
            stars=stars,
            min_price=min_price,
            max_price=max_price,
            page=page,
            per_page=per_page,
            check_in=check_in,
            check_out=check_out,
            filtered_hotels=filtered_hotels
        )

    async def get_hotel_by_id(
        self,
        hotel_id: int,
        location_code: str = None,
        check_in: str = None,
        check_out: str = None
    ) -> Optional[dict]:
        """Получить отель по ID"""
        return await self.hotels_loader.get_hotel_by_id(
            hotel_id=hotel_id,
            location_code=location_code,
            check_in=check_in,
            check_out=check_out
        )

    async def get_room_by_id(self, hotel_id: int, room_id: int, check_in: str = None, check_out: str = None) -> Optional[dict]:
        """Получить номер по ID с ценой для указанных дат"""
        return await self.hotels_loader.get_room_by_id(hotel_id=hotel_id, room_id=room_id, check_in=check_in, check_out=check_out)

    async def get_all_locations(self) -> list:
        """Получить все доступные локации/острова"""
        return await self.hotels_loader.get_all_locations()

    # ========== ЭКСКУРСИИ (делегирование в ExcursionsLoader) ==========

    async def get_excursions_by_filters(
        self,
        island: str = None,
        excursion_type: str = None,
        date: str = None
    ) -> list:
        """Получить экскурсии по фильтрам"""
        return await self.excursions_loader.get_excursions_by_filters(
            island=island,
            excursion_type=excursion_type,
            date=date
        )

    async def get_excursion_by_id(self, excursion_id: str) -> dict:
        """Получить экскурсию по ID"""
        return await self.excursions_loader.get_excursion_by_id(excursion_id)

    async def get_companions_by_month(self, island: str, year: int, month: int) -> list:
        """Получить экскурсии с поиском попутчиков за месяц"""
        return await self.excursions_loader.get_companions_by_month(island, year, month)

    # ========== ПАКЕТНЫЕ ТУРЫ (делегирование в PackagesLoader) ==========

    def get_packages_by_date(self, target_date: str = None) -> list:
        """Получить пакетные туры близкие к указанной дате"""
        return self.packages_loader.get_packages_by_date(target_date)

    def get_package_by_id(self, package_id: str) -> dict:
        """Получить пакетный тур по ID"""
        return self.packages_loader.get_package_by_id(package_id)

    # ========== ТРАНСФЕРЫ (делегирование в TransfersLoader) ==========

    async def get_transfers_by_island(self, island: str = None) -> list:
        """Получить трансферы по острову"""
        return await self.transfers_loader.get_transfers_by_island(island)

    async def get_transfer_by_id(self, transfer_id: str) -> dict:
        """Получить трансфер по ID"""
        return await self.transfers_loader.get_transfer_by_id(transfer_id)


# Глобальный экземпляр (будет инициализирован с API в bot.py)
_data_loader_instance = None


def get_data_loader() -> DataLoader:
    """Получить экземпляр DataLoader"""
    if _data_loader_instance is None:
        raise RuntimeError("DataLoader не инициализирован! Вызовите set_data_loader() в bot.py")
    return _data_loader_instance


def set_data_loader(api: PelagosAPI):
    """Установить экземпляр DataLoader"""
    global _data_loader_instance
    _data_loader_instance = DataLoader(api=api)