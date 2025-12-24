"""Сервис для работы с Order API Pelagos (POST запросы)"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .api_client import APIClient

logger = logging.getLogger(__name__)


class OrderAPI:
    """Класс для работы с Order API Pelagos (создание и управление заказами)"""

    def __init__(self, api_key: str = None):
        self.client = APIClient(
            base_url="https://app.pelagos.ru",
            api_key=api_key,
            timeout=30
        )

    # === СОЗДАНИЕ И УПРАВЛЕНИЕ ЗАКАЗАМИ ===

    async def create_order(
        self,
        client_name: str = "",
        agent_name: str = "",
        group_members: str = "",
        flight_info: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Создать новый заказ

        POST /order-api/create/

        Args:
            client_name: Имя клиента
            agent_name: Имя агента
            group_members: Имена и фамилии всех членов группы на английском языке
            flight_info: Полётная информация для организации трансферов

        Returns:
            dict с данными созданного заказа (включая order_id) или None
        """
        endpoint = "order-api/create/"

        payload = {}
        if client_name:
            payload["client_name"] = client_name
        if agent_name:
            payload["agent_name"] = agent_name
        if group_members:
            payload["group_members"] = group_members
        if flight_info:
            payload["flight_info"] = flight_info

        logger.info(f"📤 Создание заказа для клиента: {client_name}")

        try:
            data = await self.client.post(endpoint, json={"payload": payload})

            if data and data.get("code") == "OK":
                order_id = data.get("order_id")
                logger.info(f"✅ Заказ создан успешно. ID: {order_id}")
                return data
            else:
                logger.error(f"❌ Ошибка создания заказа: {data}")
                return None

        except Exception as e:
            logger.error(f"❌ Исключение при создании заказа: {e}", exc_info=True)
            return None

    async def update_order(
        self,
        order_id: int,
        client_name: str = None,
        agent_name: str = None,
        group_members: str = None,
        flight_info: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Изменить параметры заказа

        POST /order-api/update/{order_id}/

        Args:
            order_id: ID заказа
            client_name: Имя клиента
            agent_name: Имя агента
            group_members: Имена и фамилии всех членов группы
            flight_info: Полётная информация

        Returns:
            dict с результатом обновления или None
        """
        endpoint = f"order-api/update/{order_id}/"

        payload = {}
        if client_name is not None:
            payload["client_name"] = client_name
        if agent_name is not None:
            payload["agent_name"] = agent_name
        if group_members is not None:
            payload["group_members"] = group_members
        if flight_info is not None:
            payload["flight_info"] = flight_info

        logger.info(f"📤 Обновление заказа #{order_id}")

        try:
            data = await self.client.post(endpoint, json={"payload": payload})

            if data and data.get("code") == "OK":
                logger.info(f"✅ Заказ #{order_id} обновлен")
                return data
            else:
                logger.error(f"❌ Ошибка обновления заказа: {data}")
                return None

        except Exception as e:
            logger.error(f"❌ Исключение при обновлении заказа: {e}", exc_info=True)
            return None

    async def load_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Загрузить информацию об имеющемся заказе

        GET /order-api/load/{order_id}/

        Args:
            order_id: ID заказа

        Returns:
            dict с данными заказа или None
        """
        endpoint = f"order-api/load/{order_id}/"

        logger.info(f"📥 Загрузка заказа #{order_id}")

        try:
            data = await self.client.get(endpoint)

            if data and data.get("code") == "OK":
                logger.info(f"✅ Заказ #{order_id} загружен")
                return data
            else:
                logger.error(f"❌ Ошибка загрузки заказа: {data}")
                return None

        except Exception as e:
            logger.error(f"❌ Исключение при загрузке заказа: {e}", exc_info=True)
            return None

    async def get_order_parts(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить состав (список пунктов) заказа

        GET /order-api/parts/{order_id}/

        Args:
            order_id: ID заказа

        Returns:
            dict с ключами: lst (список пунктов), totals (итоговые суммы) или None
        """
        endpoint = f"order-api/parts/{order_id}/"

        logger.info(f"📥 Загрузка пунктов заказа #{order_id}")

        try:
            data = await self.client.get(endpoint)

            if data and data.get("code") == "OK":
                parts_count = len(data.get("lst", []))
                logger.info(f"✅ Загружено {parts_count} пунктов заказа #{order_id}")
                return data
            else:
                logger.error(f"❌ Ошибка загрузки пунктов заказа: {data}")
                return None

        except Exception as e:
            logger.error(f"❌ Исключение при загрузке пунктов заказа: {e}", exc_info=True)
            return None

    async def add_order_part(
        self,
        order_id: int,
        service_id: int,
        check_in: str = None,
        check_out: str = None,
        quantity: int = 1,
        adults: int = 2,
        children_with_bed: int = 0,
        children_without_bed: int = 0,
        breakfast: bool = False,
        lunch: bool = False,
        dinner: bool = False,
        extra_price: float = 0,
        rooming_list: str = "",
        transfer_request: str = "",
        flight_info: str = "",
        hotel_comment: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Добавить пункт в заказ

        POST /order-api/addpart/{order_id}/

        Args:
            order_id: ID заказа
            service_id: ID номера или услуги
            check_in: Дата заезда (YYYY-MM-DD или DD.MM.YYYY)
            check_out: Дата выезда (YYYY-MM-DD или DD.MM.YYYY)
            quantity: Количество номеров/услуг
            adults: Количество взрослых в каждом номере
            children_with_bed: Количество детей с отдельным местом
            children_without_bed: Количество детей без места (до 12 лет)
            breakfast: Завтрак включен
            lunch: Обед включен
            dinner: Ужин включен
            extra_price: Добавка к базовой цене (USD)
            rooming_list: Имена и фамилии на английском (руминг лист)
            transfer_request: Запрос на трансфер отеля
            flight_info: Полётная информация для встречи отелем
            hotel_comment: Комментарий для отеля

        Returns:
            dict с результатом добавления или None
        """
        endpoint = f"order-api/addpart/{order_id}/"

        payload = {
            "service_id": service_id,
            "quantity": quantity,
            "adults": adults,
            "children_with_bed": children_with_bed,
            "children_without_bed": children_without_bed,
            "extra_price": extra_price
        }

        # Добавляем опциональные поля
        if check_in:
            payload["check_in"] = check_in
        if check_out:
            payload["check_out"] = check_out
        if breakfast:
            payload["breakfast"] = breakfast
        if lunch:
            payload["lunch"] = lunch
        if dinner:
            payload["dinner"] = dinner
        if rooming_list:
            payload["rooming_list"] = rooming_list
        if transfer_request:
            payload["transfer_request"] = transfer_request
        if flight_info:
            payload["flight_info"] = flight_info
        if hotel_comment:
            payload["hotel_comment"] = hotel_comment

        logger.info(f"📤 Добавление пункта в заказ #{order_id}: service_id={service_id}")

        try:
            data = await self.client.post(endpoint, json={"payload": payload})

            if data and data.get("code") == "OK":
                logger.info(f"✅ Пункт добавлен в заказ #{order_id}")
                return data
            else:
                logger.error(f"❌ Ошибка добавления пункта: {data}")
                return None

        except Exception as e:
            logger.error(f"❌ Исключение при добавлении пункта: {e}", exc_info=True)
            return None

    async def close(self):
        """Закрыть соединение"""
        await self.client.close()