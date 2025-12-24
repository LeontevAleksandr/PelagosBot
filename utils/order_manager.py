"""Простой менеджер заказов"""
from utils.helpers import convert_price


class OrderManager:
    """Управление заказом в состоянии пользователя"""

    @staticmethod
    def get_order(state_data: dict) -> list:
        """Получить текущий заказ"""
        return state_data.get("order", [])

    @staticmethod
    def add_hotel(state_data: dict, hotel: dict, room: dict, nights: int, check_in: str = None, check_out: str = None) -> dict:
        """Добавить отель в заказ"""
        order = state_data.get("order", [])

        total_price = room["price"] * nights

        order.append({
            "type": "hotel",
            "name": f"{hotel['name']} - {room['name']}",
            "details": f"{nights} ноч.",
            "price_usd": total_price,
            # Дополнительные данные для API
            "service_id": room.get("id", 0),
            "check_in": check_in,
            "check_out": check_out,
            "quantity": 1,
            "adults": 2,  # По умолчанию 2 взрослых
            "children_with_bed": 0,
            "children_without_bed": 0
        })

        state_data["order"] = order
        return state_data

    @staticmethod
    def add_excursion(state_data: dict, excursion: dict, people_count: int = 1) -> dict:
        """Добавить экскурсию в заказ"""
        order = state_data.get("order", [])

        # Для индивидуальных экскурсий используем price_list
        price_list = excursion.get('price_list', {})

        if price_list and people_count in price_list:
            # Цена за человека для указанного количества людей
            price_per_person = price_list[people_count]
            # Общая стоимость = цена_за_человека × количество
            total_price = price_per_person * people_count
        else:
            # Для групповых экскурсий или если нет price_list
            total_price = excursion.get("price_usd", 0) * people_count

        details = f"{people_count} чел." if people_count > 1 else ""

        order.append({
            "type": "excursion",
            "name": excursion["name"],
            "details": details,
            "price_usd": total_price,
            # Дополнительные данные для API
            "service_id": int(excursion.get("service_id", 0)) if excursion.get("service_id") else 0,
            "date": excursion.get("date"),  # Дата экскурсии
            "people_count": people_count
        })

        state_data["order"] = order
        return state_data

    @staticmethod
    def add_package(state_data: dict, package: dict) -> dict:
        """Добавить пакетный тур в заказ"""
        order = state_data.get("order", [])

        order.append({
            "type": "package",
            "name": package["name"],
            "details": f"{package['duration']} дней",
            "price_usd": package["price_usd"],
            # Дополнительные данные для API
            "service_id": package.get("id", 0),
            "adults": package.get("adults", 2)
        })

        state_data["order"] = order
        return state_data

    @staticmethod
    def add_transfer(state_data: dict, transfer: dict, people_count: int) -> dict:
        """Добавить трансфер в заказ"""
        order = state_data.get("order", [])

        total_price = transfer["price_per_person_usd"] * people_count

        order.append({
            "type": "transfer",
            "name": transfer["name"],
            "details": f"{people_count} чел.",
            "price_usd": total_price,
            # Дополнительные данные для API
            "service_id": transfer.get("id", 0),
            "people_count": people_count,
            "flight_info": ""  # Будет заполнено при необходимости
        })

        state_data["order"] = order
        return state_data

    @staticmethod
    def remove_item(state_data: dict, index: int) -> dict:
        """Удалить элемент из заказа"""
        order = state_data.get("order", [])
        if 0 <= index < len(order):
            order.pop(index)
        state_data["order"] = order
        return state_data

    @staticmethod
    def clear_order(state_data: dict) -> dict:
        """Очистить заказ"""
        state_data["order"] = []
        return state_data

    @staticmethod
    def get_total(order: list) -> dict:
        """Получить общую сумму в разных валютах"""
        total_usd = sum(item["price_usd"] for item in order)

        return {
            "usd": total_usd,
            "rub": int(convert_price(total_usd, "usd", "rub")),
            "peso": int(convert_price(total_usd, "usd", "peso"))
        }

    @staticmethod
    def format_order(order: list) -> str:
        """Форматировать заказ для отображения"""
        if not order:
            return "Ваша корзина пуста"

        lines = ["<b>Ваш заказ:</b>\n"]

        for i, item in enumerate(order, 1):
            emoji = {
                "hotel": "🏨",
                "excursion": "🎯",
                "package": "🎁",
                "transfer": "🚗"
            }.get(item["type"], "📦")

            details = f" ({item['details']})" if item['details'] else ""
            lines.append(f"{i}. {emoji} {item['name']}{details}")
            lines.append(f"   ${item['price_usd']}\n")

        total = OrderManager.get_total(order)
        lines.append(f"<b>Итого:</b>")
        lines.append(f"💵 ${total['usd']}")
        lines.append(f"💵 {total['rub']} руб.")
        lines.append(f"💵 {total['peso']} песо")

        return "\n".join(lines)


# Глобальный экземпляр
order_manager = OrderManager()
