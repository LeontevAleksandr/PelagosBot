"""Адаптер для преобразования данных бота в формат Order API"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OrderAPIAdapter:
    """
    Класс для преобразования данных из состояния бота в формат,
    понятный для Order API Pelagos
    """

    @staticmethod
    def format_datetime(date_str: str) -> str:

        if not date_str:
            return ""

        try:
            # Если уже в формате DD.MM.YYYY, просто добавляем время
            if "." in date_str and not " " in date_str:
                return f"{date_str} 00:00"

            # Если уже с временем, возвращаем как есть
            if " " in date_str:
                return date_str

            # Если в формате YYYY-MM-DD, конвертируем
            if "-" in date_str:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return dt.strftime("%d.%m.%Y 00:00")

            return date_str

        except Exception as e:
            logger.error(f"Ошибка форматирования даты {date_str}: {e}")
            return date_str

    @staticmethod
    def prepare_order_data(state_data: dict) -> Dict[str, Any]:

        user_name = state_data.get("user_name", "")
        user_phone = state_data.get("user_phone", "")

        # Формируем имя клиента
        client_name = user_name if user_name else "Клиент из бота"

        # Имя агента (бот)
        agent_name = "Pelagos Bot"

        return {
            "client_name": client_name,
            "agent_name": agent_name,
            "names": "",  # Имена туристов
            "descr": "",  # Описание заказа
            "tourist_phone": user_phone  # Номер телефона туриста
        }

    @staticmethod
    def convert_hotel_item_to_part(
        hotel_item: dict,
        state_data: dict
    ) -> Dict[str, Any]:

        user_name = state_data.get("user_name", "")
        user_phone = state_data.get("user_phone", "")

        # Извлекаем данные из hotel_item
        check_in = hotel_item.get("check_in", "")
        check_out = hotel_item.get("check_out", "")
        hotel_id = hotel_item.get("hotel_id", 0)
        room_id = hotel_item.get("service_id", 0)  # object_id это ID номера
        quantity = hotel_item.get("quantity", 1)

        # Форматируем даты в "DD.MM.YYYY HH:MM"
        stime = OrderAPIAdapter.format_datetime(check_in)
        etime = OrderAPIAdapter.format_datetime(check_out)

        return {
            "client_name": user_name,
            "agent_name": "Pelagos Bot",
            "names": "",
            "descr": f"Бронирование через Telegram бот",
            "tab": "hotel",
            "hotel_id": hotel_id,
            "stime": stime,
            "etime": etime,
            "object_id": room_id,
            "multi": str(quantity)
        }

    @staticmethod
    def convert_excursion_item_to_part(
        excursion_item: dict,
        state_data: dict
    ) -> Dict[str, Any]:

        people_count = excursion_item.get("people_count", 1)

        excursion_id = excursion_item.get("service_id", 0)
        excursion_type = excursion_item.get("excursion_type", "unknown")

        logger.info(f"📋 Конвертация экскурсии: service_id={excursion_id}, type={excursion_type}, people={people_count}")

        excursion_date = excursion_item.get("date", "")
        excursion_time = excursion_item.get("time", "00:00")
        duration_minutes = excursion_item.get("duration", 180)  # По умолчанию 3 часа

        stime = ""
        etime = ""

        if excursion_date:
            try:
                date_time_str = f"{excursion_date} {excursion_time or '00:00'}"
                dt_start = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")

                stime = dt_start.strftime("%d.%m.%Y %H:%M")

                if duration_minutes and duration_minutes > 0:
                    dt_end = dt_start + timedelta(minutes=duration_minutes)
                else:
                    dt_end = dt_start + timedelta(hours=3)

                etime = dt_end.strftime("%d.%m.%Y %H:%M")

            except Exception as e:
                logger.error(f"Ошибка форматирования времени для экскурсии: {e}")
                # Fallback: используем только дату с временем 00:00 и +3 часа
                stime = OrderAPIAdapter.format_datetime(excursion_date)
                try:
                    dt = datetime.strptime(excursion_date, "%Y-%m-%d")
                    dt_end = dt + timedelta(hours=3)
                    etime = dt_end.strftime("%d.%m.%Y %H:%M")
                except:
                    etime = stime

        result = {
            "tab": "transfer",
            "object_id": excursion_id,
            "adults": str(people_count)
        }

        # только stime
        if stime:
            result["stime"] = stime

        logger.info(f"✅ Результат конвертации: {result}")
        return result

    @staticmethod
    def convert_transfer_item_to_part(
        transfer_item: dict,
        state_data: dict
    ) -> Dict[str, Any]:
    
        user_name = state_data.get("user_name", "")

        # Извлекаем количество человек из details
        details = transfer_item.get("details", "")
        people_count = 1

        if "чел." in details:
            try:
                people_count = int(details.split()[0])
            except (ValueError, IndexError):
                people_count = 1

        # ID трансфера
        transfer_id = transfer_item.get("service_id", 0)

        # Дата трансфера
        transfer_date = transfer_item.get("date", "")
        stime = OrderAPIAdapter.format_datetime(transfer_date)
        etime = stime  # Для трансферов совпадает

        # hotel_id может быть передан если есть
        hotel_id = transfer_item.get("hotel_id", 0)

        # Информация о рейсе если есть
        flight_info = transfer_item.get("flight_info", "")
        descr = f"Трансфер для {people_count} чел. через Telegram бот"
        if flight_info:
            descr += f". Рейс: {flight_info}"

        return {
            "client_name": user_name,
            "agent_name": "Pelagos Bot",
            "names": "",
            "descr": descr,
            "tab": "transfer",
            "hotel_id": hotel_id,
            "stime": stime,
            "etime": etime,
            "object_id": transfer_id,
            "multi": str(people_count)
        }

    @staticmethod
    def convert_package_item_to_part(
        package_item: dict,
        state_data: dict
    ) -> Dict[str, Any]:

        # ID пакетного тура
        package_id = package_item.get("service_id", 0)

        # Дата пакетного тура (YYYY-MM-DD → DD.MM.YYYY HH:MM)
        package_date = package_item.get("date", "")
        stime = OrderAPIAdapter.format_datetime(package_date)

        # Количество человек
        people_count = package_item.get("people_count", 1)

        result = {
            "tab": "transfer",
            "object_id": package_id,
            "stime": stime,
            "multi": "",
            "adults": str(people_count)
        }

        logger.info(f"📋 Конвертация пакетного тура: service_id={package_id}, date={package_date} → stime={stime}, people={people_count}")

        return result

    @staticmethod
    def convert_order_to_parts(
        order: List[dict],
        state_data: dict
    ) -> List[Dict[str, Any]]:
        
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
    def build_channel_message(order_items: List[dict], state_data: dict) -> str:
        """
        Сформировать текст уведомления о новой заявке для административного канала.

        Args:
            order_items: список позиций заказа из корзины
            state_data: данные FSM состояния (telegram_username, phone_number, user_phone)

        Returns:
            Текст сообщения в формате Markdown
        """
        phone = state_data.get("phone_number") or state_data.get("user_phone", "")
        username = state_data.get("telegram_username")

        lines = ["*[Новая заявка] Пелагос (Telegram Bot)*"]

        for item in order_items:
            item_type = item.get("type", "")
            # Убираем символы, ломающие markdown
            name = (item.get("name") or "").replace("*", "").replace("[", "").replace("]", "").replace("`", "")

            lines.append("")
            lines.append(f"Услуга: *{name}*")

            if item_type == "hotel":
                check_in = item.get("check_in") or "уточняется"
                check_out = item.get("check_out") or "уточняется"
                quantity = item.get("quantity", 1)
                lines.append(f"Заезд: {check_in}")
                lines.append(f"Выезд: {check_out}")
                lines.append(f"Номеров: {quantity}")
            else:
                date = item.get("date") or ""
                people_count = item.get("people_count") or 1
                lines.append(f"Дата: {date if date else 'уточняется'}")
                lines.append(f"Кол-во: {people_count}")

        lines.append("")
        lines.append("Канал: Telegram")
        if username:
            lines.append(f"Telegram: @{username}")
        if phone:
            lines.append(f"Телефон: {phone}")

        return "\n".join(lines)


# Глобальный экземпляр
order_api_adapter = OrderAPIAdapter()