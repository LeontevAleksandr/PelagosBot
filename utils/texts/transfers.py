"""Тексты для флоу трансферов"""


def get_transfers_intro_text(name: str) -> str:
    """Вступительное сообщение о трансферах"""
    return f"{name}, для организации трансфера выберите направление:"


def get_transfer_card_text(transfer: dict, people_count: int) -> str:
    """Форматирование карточки трансфера"""
    price_usd = transfer['price_per_person_usd'] * people_count
    price_rub = int(price_usd * 99)
    price_peso = int(price_usd * 60.5)

    return f"""<b>{transfer['name']}</b>

{transfer['description']}

👥 Количество человек: {people_count}

💵 Стоимость:
• ${price_usd}
• {price_rub} руб.
• {price_peso} песо"""


def get_transfer_booking_text(transfer_name: str, people_count: int) -> str:
    """Текст при бронировании трансфера"""
    return f"""Спасибо за заказ трансфера "{transfer_name}" для {people_count} чел.

Поделитесь своими данными и один из наших менеджеров свяжется с вами, чтобы уточнить детали."""
