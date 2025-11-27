"""Простой менеджер заказов"""
from utils.helpers import convert_price


class OrderManager:
    """Управление заказом в состоянии пользователя"""

    @staticmethod
    def get_order(state_data: dict) -> list:
        """Получить текущий заказ"""
        return state_data.get("order", [])

    @staticmethod
    def add_hotel(state_data: dict, hotel: dict, room: dict, nights: int) -> dict:
        """Добавить отель в заказ"""
        order = state_data.get("order", [])

        total_price = room["price"] * nights

        order.append({
            "type": "hotel",
            "name": f"{hotel['name']} - {room['name']}",
            "details": f"{nights} ноч.",
            "price_usd": total_price
        })

        state_data["order"] = order
        return state_data

    @staticmethod
    def add_excursion(state_data: dict, excursion: dict, people_count: int = 1) -> dict:
        """Добавить экскурсию в заказ"""
        order = state_data.get("order", [])

        total_price = excursion["price_usd"] * people_count
        details = f"{people_count} чел." if people_count > 1 else ""

        order.append({
            "type": "excursion",
            "name": excursion["name"],
            "details": details,
            "price_usd": total_price
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
            "price_usd": package["price_usd"]
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
            "price_usd": total_price
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
