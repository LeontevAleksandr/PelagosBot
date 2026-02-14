"""Тексты для флоу пакетных туров"""
from utils.helpers import convert_price


def get_packages_intro_text(name: str) -> str:
    """Вступительное сообщение о пакетных турах"""
    return f"""{name}, отличный выбор. Пакетные туры позволяют охватить большее количество островов, познакомиться с интересными людьми и при этом сэкономить.

На какие даты вам предложить туры?"""


def get_package_card_text(package: dict) -> str:
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

    # Цена
    price_usd = package.get('price_usd')
    if price_usd:
        price_rub = int(convert_price(price_usd, "usd", "rub"))
        price_peso = int(convert_price(price_usd, "usd", "peso"))
        text += f"\n💵 ${price_usd} / {price_rub} руб. / {price_peso} песо\n"
    elif not package.get('prices_loaded'):
        text += "\n💵 Цена по запросу\n"

    return text


def get_package_booking_text(package_name: str, date: str) -> str:
    """Текст при бронировании пакетного тура"""
    return f"""Вы выбрали тур "<b>{package_name}</b>" на {date}.

Поделитесь своими данными и один из наших менеджеров свяжется с вами, чтобы обсудить детали."""
