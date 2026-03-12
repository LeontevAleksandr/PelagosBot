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
        names: str = "",
        descr: str = "",
        tourist_phone: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Создать новый заказ

        POST /order-api/create/

        Args:
            client_name: Имя клиента
            agent_name: Имя агента
            names: Имена и фамилии всех членов группы
            descr: Описание/примечания к заказу
            tourist_phone: Номер телефона туриста

        Returns:
            dict с данными созданного заказа (включая order_id) или None
        """
        endpoint = "order-api/create/"

        payload = {
            "client_name": client_name,
            "agent_name": agent_name,
            "names": names,
            "descr": descr
        }

        # Добавляем tourist_phone если передан
        if tourist_phone:
            payload["tourist_phone"] = tourist_phone

        logger.info(f"📤 Создание заказа для клиента: {client_name}")

        try:
            request_body = {"payload": payload}
            logger.info(f"   POST {endpoint}")
            logger.info(f"   Тело запроса: {request_body}")

            data = await self.client.post(endpoint, json=request_body)

            logger.info(f"   Ответ API: {data}")

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
        names: str = None,
        descr: str = None,
        tourist_phone: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Изменить параметры заказа

        POST /order-api/update/{order_id}/

        Args:
            order_id: ID заказа
            client_name: Имя клиента
            agent_name: Имя агента
            names: Имена и фамилии всех членов группы
            descr: Описание/примечания к заказу
            tourist_phone: Номер телефона туриста

        Returns:
            dict с результатом обновления или None
        """
        endpoint = f"order-api/savepart/{order_id}/"

        payload = {}
        if client_name is not None:
            payload["client_name"] = client_name
        if agent_name is not None:
            payload["agent_name"] = agent_name
        if names is not None:
            payload["names"] = names
        if descr is not None:
            payload["descr"] = descr
        if tourist_phone is not None:
            payload["tourist_phone"] = tourist_phone

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
        client_name: str = "",
        agent_name: str = "",
        names: str = "",
        descr: str = "",
        tab: str = "",
        hotel_id: int = None,
        stime: str = "",
        etime: str = "",
        object_id: int = None,
        multi: str = "",
        adults: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Добавить пункт в заказ

        POST /order-api/addpart/{order_id}/

        Args:
            order_id: ID заказа
            client_name: Имя клиента
            agent_name: Имя агента
            names: Имена туристов
            descr: Описание
            tab: Тип услуги (hotel, transfer, excursion, package)
            hotel_id: ID отеля (для всех типов услуг)
            stime: Время начала в формате "DD.MM.YYYY HH:MM"
            etime: Время окончания в формате "DD.MM.YYYY HH:MM"
            object_id: ID объекта (номер, экскурсия, трансфер и т.д.)
            multi: Количество (строка, например "2")
            adults: Количество взрослых (строка, используется для экскурсий/трансферов)

        Returns:
            dict с результатом добавления или None
        """
        endpoint = f"order-api/addpart/{order_id}/"

        payload = {}

        # Добавляем только непустые поля
        if tab:
            payload["tab"] = tab
        if client_name:
            payload["client_name"] = client_name
        if agent_name:
            payload["agent_name"] = agent_name
        if names:
            payload["names"] = names
        if descr:
            payload["descr"] = descr
        if stime:
            payload["stime"] = stime
        if etime:
            payload["etime"] = etime
        if multi:
            payload["multi"] = multi
        if adults:
            payload["adults"] = adults
        if hotel_id is not None:
            payload["hotel_id"] = hotel_id
        if object_id is not None:
            payload["object_id"] = object_id

        logger.info(f"📤 Добавление пункта в заказ #{order_id}: tab={tab}, object_id={object_id}")
        logger.debug(f"   Полный payload: {payload}")

        try:
            request_body = {"payload": payload}
            logger.info(f"   POST {endpoint}")
            logger.info(f"   Тело запроса: {request_body}")

            data = await self.client.post(endpoint, json=request_body)

            logger.info(f"   Ответ API: {data}")

            if data and data.get("code") == "OK":
                part_id = data.get("part_id")
                logger.info(f"✅ Пункт добавлен в заказ #{order_id}, part_id={part_id}")
                return data
            else:
                logger.error(f"❌ Ошибка добавления пункта: {data}")
                return None

        except Exception as e:
            logger.error(f"❌ Исключение при добавлении пункта: {e}", exc_info=True)
            return None

    async def send_channelmsg(self, channel_id: str, msg: str) -> Optional[Dict[str, Any]]:
        """
        Отправить сообщение в администраторский канал

        POST /order-api/channelmsg/

        Args:
            channel_id: Идентификатор канала (например, "grouptours")
            msg: Текст сообщения в формате Markdown

        Returns:
            dict или None
        """
        endpoint = "order-api/channelmsg/"
        payload = {
            "channel": channel_id,
            "msg": msg,
            "parse_mode": "markdown"
        }

        logger.info(f"📢 Отправка уведомления в канал '{channel_id}'")

        try:
            data = await self.client.post(endpoint, json={"payload": payload})
            if data and data.get("code") == "OK":
                logger.info(f"✅ Уведомление отправлено в канал '{channel_id}'")
                return data
            else:
                logger.error(f"❌ Ошибка отправки в канал: {data}")
                return None
        except Exception as e:
            logger.error(f"❌ Исключение при отправке в канал: {e}", exc_info=True)
            return None

    async def close(self):
        """Закрыть соединение"""
        await self.client.close()