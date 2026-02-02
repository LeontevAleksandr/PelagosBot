"""Тексты для флоу трансферов"""


def get_transfers_intro_text(name: str) -> str:
    """Вступительное сообщение о трансферах"""
    return f"{name}, для организации трансфера выберите направление:"


def _get_price_for_people(transfer: dict, people_count: int) -> float:
    """
    Получить цену за человека для указанного количества людей

    Логика: ищём цену для grp >= people_count (чем больше группа, тем дешевле)
    """
    price_list = transfer.get('price_list', {})

    if not price_list:
        # Если нет списка цен, используем базовую цену
        base_price = transfer.get('price_per_person_usd')
        return base_price if base_price else 0

    # Ищем точное совпадение
    if people_count in price_list:
        return price_list[people_count]

    # Ищем ближайшее большее значение grp
    available_grps = sorted(price_list.keys())
    for grp in available_grps:
        if grp >= people_count:
            return price_list[grp]

    # Если people_count больше всех grp, берём максимальный grp
    if available_grps:
        return price_list[max(available_grps)]

    return 0


def get_transfer_card_text(transfer: dict, people_count: int) -> str:
    """Форматирование карточки трансфера"""
    # Получаем цену за человека для данного количества людей
    price_per_person = _get_price_for_people(transfer, people_count)

    # Если цена не загружена
    if price_per_person is None or price_per_person == 0:
        return f"""<b>{transfer['name']}</b>

{transfer['description']}

👥 Количество человек: {people_count}

💵 Стоимость: уточняйте у менеджера"""

    # Общая стоимость для всей группы
    total_price_usd = price_per_person * people_count
    price_rub = int(total_price_usd * 99)
    price_peso = int(total_price_usd * 60.5)

    return f"""<b>{transfer['name']}</b>

{transfer['description']}

👥 Количество человек: {people_count}

💵 Стоимость:
• ${int(total_price_usd)}
• {price_rub} руб.
• {price_peso} песо"""


def get_transfer_booking_text(transfer_name: str, people_count: int) -> str:
    """Текст при бронировании трансфера"""
    return f"""Спасибо за заказ трансфера "{transfer_name}" для {people_count} чел.

Поделитесь своими данными и один из наших менеджеров свяжется с вами, чтобы уточнить детали."""
