"""Загрузчик данных для пакетных туров через Pelagos API"""
import logging
from typing import Optional, Dict, List
from services.pelagos_api import PelagosAPI
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class PackagesLoader:
    """Класс для работы с пакетными турами через Pelagos API"""

    # TTL для кэша (3 часа)
    CACHE_TTL = 10800

    # Тип услуги для туров в API
    SERVICE_TYPE = 1150

    def __init__(self, api: Optional[PelagosAPI] = None, **kwargs):
        """
        Args:
            api: API для работы с турами (Pelagos API)
        """
        self.api = api
        self.cache = get_cache_manager()

    def _extract_price_list_from_plst(self, plst: List[Dict]) -> Dict[int, float]:
        """
        Извлечь список цен для разного количества человек из plst

        Args:
            plst: массив из API с ценами [{grp: 1, price: 50}, ...]

        Returns:
            dict: {количество_людей: цена_за_человека}
        """
        price_list = {}
        for item in plst:
            grp = item.get('grp')
            price = item.get('price')
            if grp and price is not None:
                price_list[grp] = float(price)
        return price_list

    async def _load_package_prices(self, package_id: int) -> Dict[int, float]:
        """
        Загрузить цены для тура по его ID

        Args:
            package_id: ID тура

        Returns:
            dict: {количество_людей: цена_за_человека}
        """
        try:
            prices_data = await self.api.get_service_prices(package_id)

            if not prices_data:
                return {}

            combined_price_list = {}
            for price_entry in prices_data:
                plst = price_entry.get('plst', [])
                price_list = self._extract_price_list_from_plst(plst)
                combined_price_list.update(price_list)

            return combined_price_list
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить цены для тура {package_id}: {e}")
            return {}

    async def get_all_packages(self) -> list:
        """
        Получить все пакетные туры

        Returns:
            list: список словарей с информацией о турах
        """
        if not self.api:
            logger.warning("⚠️ API не инициализирован")
            return []

        # Проверяем кэш
        cache_key = "packages:all"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"✓ Используем кэш пакетных туров ({len(cached)} шт)")
            return cached

        try:
            logger.info("📡 Запрос пакетных туров из API...")

            result = await self.api.get_services(
                service_type=self.SERVICE_TYPE,
                perpage=500
            )

            services = result.get("services", [])
            logger.info(f"📥 API вернул {len(services)} пакетных туров")

            packages = []
            for service in services:
                # Пропускаем детские тарифы
                if service.childrate and service.childrate > 0:
                    continue

                package_dict = {
                    'id': str(service.id),
                    'name': service.name,
                    'type': service.type,
                    'subtype': service.subtype,
                    'russian_guide': bool(service.russian_guide) if service.russian_guide else False,
                    'lunch_included': bool(service.lunch_included) if service.lunch_included else False,
                    'private_transport': bool(service.private_transport) if service.private_transport else False,
                    'tickets_included': bool(service.tickets_included) if service.tickets_included else False,
                    'inhttp': service.inhttp,
                    'pics': service.pics,
                    'description': '',
                    # Цены загружаются отдельно
                    'price_usd': None,
                    'price_list': {},
                    'prices_loaded': False,
                }

                # Извлекаем URL первого фото
                if service.pics and len(service.pics) > 0:
                    first_pic = service.pics[0]
                    if isinstance(first_pic, dict) and 'md5' in first_pic and 'ext' in first_pic:
                        package_dict['photo'] = (
                            f"https://app.pelagos.ru/pic/{first_pic['md5']}/{first_pic['md5']}.{first_pic['ext']}"
                        )

                packages.append(package_dict)

            # Кэшируем
            self.cache.set(cache_key, packages, ttl=self.CACHE_TTL)

            logger.info(f"✅ Загружено {len(packages)} пакетных туров из API")
            return packages

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки пакетных туров: {e}")
            return []

    async def get_package_by_id(self, package_id: str) -> Optional[dict]:
        """
        Получить тур по ID (без цен)

        Args:
            package_id: ID тура

        Returns:
            dict или None
        """
        if not self.api:
            return None

        try:
            # Ищем в кэше
            cache_key = "packages:all"
            cached = self.cache.get(cache_key)
            if cached:
                for pkg in cached:
                    if str(pkg['id']) == str(package_id):
                        return pkg

            # Если нет в кэше — загружаем все
            all_packages = await self.get_all_packages()
            for pkg in all_packages:
                if str(pkg['id']) == str(package_id):
                    return pkg

            logger.warning(f"⚠️ Тур с ID {package_id} не найден")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения тура {package_id}: {e}")
            return None

    async def get_package_with_prices(self, package_id: str) -> Optional[dict]:
        """
        Получить тур по ID с загрузкой цен

        Args:
            package_id: ID тура

        Returns:
            dict с ценами или None
        """
        package = await self.get_package_by_id(package_id)
        if not package:
            return None

        # Если цены уже загружены
        if package.get('prices_loaded'):
            return package

        try:
            price_list = await self._load_package_prices(int(package_id))

            if price_list:
                package['price_list'] = price_list
                # Базовая цена — для 1 человека или минимальная
                package['price_usd'] = price_list.get(1) or min(price_list.values())
                package['prices_loaded'] = True
                logger.info(f"💰 Загружены цены для тура {package_id}: {price_list}")
            else:
                logger.warning(f"⚠️ Цены для тура {package_id} не найдены")

            return package

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки цен для тура {package_id}: {e}")
            return package

    def get_price_for_people_count(self, package: dict, people_count: int) -> float:
        """
        Получить цену тура для указанного количества людей

        Args:
            package: словарь тура
            people_count: количество человек

        Returns:
            float: цена за человека
        """
        price_list = package.get('price_list', {})

        if not price_list:
            return package.get('price_usd') or 0

        # Точное совпадение
        if people_count in price_list:
            return price_list[people_count]

        # Ближайшее большее значение grp
        available_grps = sorted(price_list.keys())
        for grp in available_grps:
            if grp >= people_count:
                return price_list[grp]

        # Максимальный grp
        if available_grps:
            return price_list[max(available_grps)]

        return 0
