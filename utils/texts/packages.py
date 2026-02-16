"""Тексты для флоу пакетных туров"""
from utils.helpers import convert_price


def get_packages_intro_text(name: str) -> str:
    """Вступительное сообщение о пакетных турах"""
    return f"""{name}, отличный выбор. Пакетные туры позволяют охватить большее количество островов, познакомиться с интересными людьми и при этом сэкономить.

Посмотрите доступные туры:"""


def get_package_card_text(package: dict, people_count: int = 1) -> str:
    """Форматирование карточки пакетного тура"""
    text = f"<b>{package['name']}</b>\n"

    # Включённые услуги
    includes = []
    if package.get('russian_guide'):
        includes.append("🗣 Русскоговорящий гид")
    if package.get('lunch_included'):
        includes.append("🍽 Питание включено")
    if package.get('private_transport'):
        includes.append("🚗 Транспорт включён")
    if package.get('tickets_included'):
        includes.append("🎫 Билеты включены")

    if includes:
        text += "\n" + "\n".join(includes) + "\n"

    # Цена для выбранного количества людей
    price_list = package.get('price_list', {})
    if price_list:
        # Ищем цену для нужного grp
        price_per_person = price_list.get(people_count)
        if price_per_person is None:
            available = sorted(price_list.keys())
            for grp in available:
                if grp >= people_count:
                    price_per_person = price_list[grp]
                    break
            if price_per_person is None and available:
                price_per_person = price_list[max(available)]

        if price_per_person:
            total = price_per_person * people_count
            total_rub = int(convert_price(total, "usd", "rub"))
            total_peso = int(convert_price(total, "usd", "peso"))
            per_person_rub = int(convert_price(price_per_person, "usd", "rub"))
            per_person_peso = int(convert_price(price_per_person, "usd", "peso"))

            text += f"\n👥 {people_count} чел. × ${price_per_person} / {per_person_rub} руб. / {per_person_peso} песо"
            text += f"\n💰 <b>Итого: ${total} / {total_rub} руб. / {total_peso} песо</b>\n"
    elif not package.get('prices_loaded'):
        text += "\n💵 Цена по запросу\n"

    return text


def get_package_summary_text(package_name: str, date: str, people_count: int, price_per_person: float) -> str:
    """Итоговый текст перед бронированием"""
    total_price = price_per_person * people_count
    total_rub = int(convert_price(total_price, "usd", "rub"))
    total_peso = int(convert_price(total_price, "usd", "peso"))
    per_person_rub = int(convert_price(price_per_person, "usd", "rub"))
    per_person_peso = int(convert_price(price_per_person, "usd", "peso"))

    text = f"""<b>{package_name}</b>

📅 Дата: {date}
👥 Количество: {people_count} чел.

💵 Цена за человека: ${price_per_person} / {per_person_rub} руб. / {per_person_peso} песо
💰 <b>Итого: ${total_price} / {total_rub} руб. / {total_peso} песо</b>"""

    return text


def get_package_booking_text(package_name: str, date: str) -> str:
    """Текст при бронировании пакетного тура"""
    return f"""Вы выбрали тур "<b>{package_name}</b>" на {date}.

Поделитесь своими данными и один из наших менеджеров свяжется с вами, чтобы обсудить детали."""
