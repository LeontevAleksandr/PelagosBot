"""Адаптер для преобразования данных бота в формат Order API"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderAPIAdapter:
    """
    Класс для преобразования данных из состояния бота в формат,
    понятный для Order API Pelagos
    """

    @staticmethod
    def prepare_order_data(state_data: dict) -> Dict[str, Any]:
        """
        Подготовить данные заказа для создания через API

        Args:
            state_data: данные из FSM состояния бота

        Returns:
            dict с данными для создания заказа
        """
        user_name = state_data.get("user_name", "")
        user_phone = state_data.get("user_phone", "")

        # Формируем имя клиента
        client_name = f"{user_name}"
        if user_phone:
            client_name += f" ({user_phone})"

        # Имя агента (бот)
        agent_name = "Pelagos Bot"

        return {
            "client_name": client_name,
            "agent_name": agent_name,
            "group_members": "",  # Будет заполнено при добавлении пунктов
            "flight_info": ""  # Будет заполнено при необходимости
        }

    @staticmethod
    def convert_hotel_item_to_part(
        hotel_item: dict,
        state_data: dict
    ) -> Dict[str, Any]:
        """
        Преобразовать элемент отеля из корзины в формат пункта заказа

        Args:
            hotel_item: элемент корзины типа "hotel"
            state_data: данные из FSM состояния

        Returns:
            dict с параметрами для add_order_part
        """
        # Извлекаем данные из hotel_item
        # Формат: {"type": "hotel", "name": "Hotel - Room", "details": "5 ноч.", "price_usd": 500}

        # Для полной интеграции нужно сохранять больше данных при добавлении в корзину
        # Пока возвращаем базовую структуру

        logger.warning("⚠️ Преобразование отелей требует расширения данных в корзине")

        return {
            "service_id": hotel_item.get("service_id", 0),
            "check_in": hotel_item.get("check_in"),
            "check_out": hotel_item.get("check_out"),
            "quantity": hotel_item.get("quantity", 1),
            "adults": hotel_item.get("adults", 2),
            "children_with_bed": hotel_item.get("children_with_bed", 0),
            "children_without_bed": hotel_item.get("children_without_bed", 0),
            "extra_price": 0,
            "rooming_list": state_data.get("user_name", ""),
            "hotel_comment": f"Заказ через Telegram бот. Телефон: {state_data.get('user_phone', '')}"
        }

    @staticmethod
    def convert_excursion_item_to_part(
        excursion_item: dict,
        state_data: dict
    ) -> Dict[str, Any]:
        """
        Преобразовать элемент экскурсии из корзины в формат пункта заказа

        Args:
            excursion_item: элемент корзины типа "excursion"
            state_data: данные из FSM состояния

        Returns:
            dict с параметрами для add_order_part
        """
        # Извлекаем количество человек из details
        # Формат details: "3 чел." или ""
        details = excursion_item.get("details", "")
        people_count = 1

        if "чел." in details:
            try:
                people_count = int(details.split()[0])
            except (ValueError, IndexError):
                people_count = 1

        # ID сервиса экскурсии
        service_id = excursion_item.get("service_id", 0)

        # Дата экскурсии (если есть)
        excursion_date = excursion_item.get("date")

        return {
            "service_id": service_id,
            "check_in": excursion_date,  # Для экскурсий это дата проведения
            "check_out": excursion_date,  # Совпадает с check_in для экскурсий
            "quantity": 1,  # Всегда 1 экскурсия
            "adults": people_count,  # Количество человек
            "children_with_bed": 0,
            "children_without_bed": 0,
            "extra_price": 0,
            "rooming_list": state_data.get("user_name", ""),
            "hotel_comment": f"Экскурсия для {people_count} чел. Телефон: {state_data.get('user_phone', '')}"
        }

    @staticmethod
    def convert_transfer_item_to_part(
        transfer_item: dict,
        state_data: dict
    ) -> Dict[str, Any]:
        """
        Преобразовать элемент трансфера из корзины в формат пункта заказа

        Args:
            transfer_item: элемент корзины типа "transfer"
            state_data: данные из FSM состояния

        Returns:
            dict с параметрами для add_order_part
        """
        # Извлекаем количество человек из details
        details = transfer_item.get("details", "")
        people_count = 1

        if "чел." in details:
            try:
                people_count = int(details.split()[0])
            except (ValueError, IndexError):
                people_count = 1

        service_id = transfer_item.get("service_id", 0)

        return {
            "service_id": service_id,
            "quantity": 1,
            "adults": people_count,
            "children_with_bed": 0,
            "children_without_bed": 0,
            "extra_price": 0,
            "transfer_request": "Запрос через Telegram бот",
            "flight_info": transfer_item.get("flight_info", ""),
            "hotel_comment": f"Трансфер для {people_count} чел. Телефон: {state_data.get('user_phone', '')}"
        }

    @staticmethod
    def convert_package_item_to_part(
        package_item: dict,
        state_data: dict
    ) -> Dict[str, Any]:
        """
        Преобразовать элемент пакетного тура из корзины в формат пункта заказа

        Args:
            package_item: элемент корзины типа "package"
            state_data: данные из FSM состояния

        Returns:
            dict с параметрами для add_order_part
        """
        service_id = package_item.get("service_id", 0)

        return {
            "service_id": service_id,
            "quantity": 1,
            "adults": package_item.get("adults", 2),
            "children_with_bed": 0,
            "children_without_bed": 0,
            "extra_price": 0,
            "rooming_list": state_data.get("user_name", ""),
            "hotel_comment": f"Пакетный тур. Телефон: {state_data.get('user_phone', '')}"
        }

    @staticmethod
    def convert_order_to_parts(
        order: List[dict],
        state_data: dict
    ) -> List[Dict[str, Any]]:
        """
        Преобразовать весь заказ (корзину) в список пунктов для API

        Args:
            order: список элементов заказа из state_data["order"]
            state_data: данные из FSM состояния

        Returns:
            список словарей с параметрами для add_order_part
        """
        parts = []

        for item in order:
            item_type = item.get("type")

            try:
                if item_type == "hotel":
                    part = OrderAPIAdapter.convert_hotel_item_to_part(item, state_data)
                elif item_type == "excursion":
                    part = OrderAPIAdapter.convert_excursion_item_to_part(item, state_data)
                elif item_type == "transfer":
                    part = OrderAPIAdapter.convert_transfer_item_to_part(item, state_data)
                elif item_type == "package":
                    part = OrderAPIAdapter.convert_package_item_to_part(item, state_data)
                else:
                    logger.warning(f"⚠️ Неизвестный тип элемента заказа: {item_type}")
                    continue

                parts.append(part)

            except Exception as e:
                logger.error(f"❌ Ошибка преобразования элемента {item_type}: {e}", exc_info=True)
                continue

        return parts

    @staticmethod
    def enrich_order_item_with_api_data(
        item: dict,
        service_id: int,
        additional_data: dict = None
    ) -> dict:
        """
        Обогатить элемент корзины дополнительными данными для API

        Args:
            item: элемент корзины
            service_id: ID сервиса из API
            additional_data: дополнительные данные (даты, количество и т.д.)

        Returns:
            обогащенный элемент корзины
        """
        item["service_id"] = service_id

        if additional_data:
            item.update(additional_data)

        return item


# Глобальный экземпляр
order_api_adapter = OrderAPIAdapter()
