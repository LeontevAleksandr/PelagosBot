"""Тексты для флоу экскурсий"""
from utils.helpers import convert_price, format_date


def get_excursions_intro_text(name: str) -> str:
    """Вступительное сообщение об экскурсиях"""
    return f"""Замечательно, {name}! Давайте сначала определимся на каком острове вы ищите экскурсии"""


EXCURSIONS_SELECT_TYPE = """Тип экскурсии:"""

EXCURSIONS_GROUP_INTRO = """Групповые туры идеально подходят для тех кто путешествует один или для тех, кто хочет сэкономить. Чтобы проверить есть ли групповые экскурсии на выбранном острове выберите дату."""

EXCURSIONS_PRIVATE_INTRO = """Индивидуальные экскурсии хоть и дороже, но дают вам полный контроль.

Сколько вас человек собирается ехать (взрослые и дети старше 7 лет)?"""

COMPANIONS_INTRO = """Наша система позволяет легко и быстро найти попутчиков.

Внизу список желающих найти попутчиков. Вы можете или присоединиться или создать собственную заявку."""

COMPANIONS_HOW_IT_WORKS = """**Как работает поиск попутчиков**

1️⃣ **Оставить заявку**
Ваш запрос на поиск попутчиков будет виден другим пользователям сайта, которые тоже могут присоединиться.

2️⃣ **Окончательная цена**
Окончательная цена экскурсии будет зависеть от финального количества человек.

3️⃣ **Гарантия условий**
Компания Пелагос Турс будет выступать фасилитатором, чтобы убедиться, что все условия одинаковы.

4️⃣ **Оплата**
После подтверждения, каждый участник должен будет внести предоплату в 500 рублей. Остаток вы сможете отдать гиду (или водителю) при встрече."""

COMPANIONS_SELECT_EXCURSION = """Итак, если вы согласны, выберите желаемую экскурсию."""

COMPANIONS_SELECT_DATE = """Выберите желаемую дату."""

COMPANIONS_INPUT_PEOPLE = """Укажите количество человек (взрослые и дети старше 7 лет)."""

NO_EXCURSIONS_FOUND = """😔 К сожалению, экскурсий на выбранную дату не найдено.

Попробуйте выбрать другую дату.""" # или создайте заявку на поиск попутчиков.


def get_group_excursion_card_text(excursion: dict, people_count: int = 1, expanded: bool = False) -> str:
    """Форматирование карточки групповой экскурсии"""
    price_usd = excursion['price_usd']

    # Формируем строку с ценой (фиксированная цена за человека + общая стоимость)
    if price_usd and price_usd > 0:
        # Цена за человека
        price_per_person_rub = int(convert_price(price_usd, "usd", "rub"))
        price_per_person_peso = int(convert_price(price_usd, "usd", "peso"))

        # Общая стоимость
        total_price_usd = price_usd * people_count
        total_price_rub = int(convert_price(total_price_usd, "usd", "rub"))
        total_price_peso = int(convert_price(total_price_usd, "usd", "peso"))

        price_line = f"""💵 Цена за чел.: ${price_usd} / {price_per_person_rub} руб. / {price_per_person_peso} песо

Общая стоимость ({people_count} чел.):
💰 ${total_price_usd} / {total_price_rub} руб. / {total_price_peso} песо"""
    else:
        price_line = "💵 Цена по запросу"

    text = f"""****
{excursion['name']}

📍 {excursion['island_name']}
🕐 {excursion['date']}, {excursion['time']}

{price_line}"""

    # Если развернуто - показываем описание
    if expanded and excursion.get('description'):
        text += f"\n\n📝 {excursion['description']}"

    return text


def get_private_excursion_card_text(excursion: dict, people_count: int, expanded: bool = False) -> str:
    """Форматирование карточки индивидуальной экскурсии"""

    # Проверяем, является ли это групповой ежедневной экскурсией
    is_group_daily = excursion.get('is_group_daily', False)

    price_list = excursion.get('price_list', {})

    # Для групповых ежедневных - фиксированная цена за человека (как у обычных групповых)
    if is_group_daily:
        # Цена за человека фиксированная
        price_per_person_usd = excursion.get('min_price', 0) or excursion.get('price_usd', 0)
        total_price_usd = price_per_person_usd * people_count
    else:
        # Для индивидуальных - цена зависит от количества людей
        price_per_person_usd = 0
        if price_list and people_count in price_list:
            price_per_person_usd = price_list[people_count]
        elif excursion.get('price_usd'):
            price_per_person_usd = excursion['price_usd']

        total_price_usd = price_per_person_usd * people_count

    # Формируем блок с ценой
    if total_price_usd and total_price_usd > 0:
        total_price_rub = int(convert_price(total_price_usd, "usd", "rub"))
        total_price_peso = int(convert_price(total_price_usd, "usd", "peso"))

        price_per_person_rub = int(convert_price(price_per_person_usd, "usd", "rub"))
        price_per_person_peso = int(convert_price(price_per_person_usd, "usd", "peso"))

        if is_group_daily:
            # Для групповых ежедневных - показываем как у групповых
            price_block = f"""💵 Цена за чел.: ${price_per_person_usd} / {price_per_person_rub} руб. / {price_per_person_peso} песо

Общая стоимость ({people_count} чел.):
💰 ${total_price_usd} / {total_price_rub} руб. / {total_price_peso} песо"""
        else:
            # Для индивидуальных - показываем общую стоимость
            price_block = f"""Общая стоимость:
💵 ${total_price_usd} дол.
₽ {total_price_rub} руб.
₱ {total_price_peso} песо

Цена за человека: ${price_per_person_usd} / {price_per_person_rub} руб. / {price_per_person_peso} песо"""
    else:
        price_block = "💵 Цена по запросу"

    text = f"""
{excursion['name']}

📍 {excursion.get('island_name', 'Не указан')}
👥 Количество чел.: {people_count}
"""

    # Добавляем маркер для ежедневных экскурсий
    if excursion.get('is_daily'):
        text += "⏰ Проводится ежедневно\n"

    text += f"\n{price_block}"

    # Дополнительная информация о включенных опциях
    features = []
    if excursion.get('has_russian_guide'):
        features.append("🗣 Русскоговорящий гид")
    if excursion.get('private_transport'):
        features.append("🚗 Индивидуальный транспорт")
    if excursion.get('lunch_included'):
        features.append("🍽 Обед включен")
    if excursion.get('tickets_included'):
        features.append("🎫 Билеты включены")

    if features:
        text += "\n\n" + "\n".join(features)

    # Если развернуто - показываем описание
    if expanded and excursion.get('description'):
        text += f"\n\n📝 {excursion['description']}"

    return text


def get_companions_excursion_card_text(excursion: dict) -> str:
    """Форматирование карточки экскурсии для поиска попутчиков"""
    pax = excursion.get('pax', 0)
    companions = excursion.get('companions', [])

    # Получаем price_list если есть, иначе используем обычную цену
    price_list = excursion.get('price_list', {})

    # Формируем строку с ценами
    if price_list:
        # Показываем цены для разного количества человек
        price_lines = []
        for grp in sorted(price_list.keys()):
            price_per_person_usd = price_list[grp]
            price_per_person_rub = int(convert_price(price_per_person_usd, "usd", "rub"))
            price_per_person_peso = int(convert_price(price_per_person_usd, "usd", "peso"))

            price_lines.append(
                f"• {grp} чел: ${price_per_person_usd} / {price_per_person_rub} руб. / {price_per_person_peso} песо (за чел.)"
            )

        price_block = "💵 Цены:\n" + "\n".join(price_lines[:3])  # Показываем первые 3 варианта
        if len(price_lines) > 3:
            price_block += f"\n... и еще {len(price_lines) - 3} вариантов"
    else:
        price_usd = excursion.get('price_usd', 0)
        if price_usd and price_usd > 0:
            price_rub = int(convert_price(price_usd, "usd", "rub"))
            price_peso = int(convert_price(price_usd, "usd", "peso"))
            price_block = f"💵 от ${price_usd} / {price_rub} руб. / {price_peso} песо"
        else:
            price_block = "💵 Цена по запросу"

    # Дополнительная информация о включенных опциях
    features = []
    if excursion.get('has_russian_guide'):
        features.append("🗣 Русскоговорящий гид")
    if excursion.get('private_transport'):
        features.append("🚗 Индивидуальный транспорт")
    if excursion.get('lunch_included'):
        features.append("🍽 Обед включен")
    if excursion.get('tickets_included'):
        features.append("🎫 Билеты включены")

    features_block = "\n" + "\n".join(features) if features else ""

    # Дата
    date_formatted = format_date(excursion.get('date', '')) if excursion.get('date') else 'Дата уточняется'

    # НОВОЕ: Формируем блок со списком попутчиков
    companions_block = ""
    if companions:
        companions_block = "\n\n**👥 Ищут попутчиков:**\n"
        for companion in companions[:5]:  # Показываем до 5 участников
            name = companion.get('title', 'Аноним')
            companion_pax = companion.get('pax', 1)
            phone = companion.get('phone', '')
            tg = companion.get('tg', '')

            # Формируем строку с контактами
            contacts = []
            if phone:
                contacts.append(f"📞 {phone}")
            if tg:
                contacts.append(f"💬 @{tg}")

            contact_str = ", ".join(contacts) if contacts else ""

            # Формируем строку участника
            if companion_pax > 1:
                companions_block += f"• {name} ({companion_pax} чел.)"
            else:
                companions_block += f"• {name}"

            if contact_str:
                companions_block += f" - {contact_str}"
            companions_block += "\n"

        if len(companions) > 5:
            companions_block += f"... и еще {len(companions) - 5} чел.\n"

    # Добавляем бейдж и описание
    text = f"""{excursion['name']}

**[Поиск попутчиков]**

📍 {excursion.get('island_name', 'Не указан')}
🕐 {date_formatted}
👥 уже {pax} человек{' ищут' if pax != 1 else ' ищет'} попутчиков

{price_block}{features_block}{companions_block}"""

    return text


def get_excursion_join_text(excursion_name: str) -> str:
    """Текст при присоединении к экскурсии"""
    return f"""Мы очень рады, что вы захотели присоединиться к {excursion_name}.

Поделитесь своими данными и один из наших менеджеров свяжется с вами, чтобы обсудить детали."""


def get_excursion_booking_text(excursion_name: str, people_count: int, date: str) -> str:
    """Текст при бронировании экскурсии"""
    return f"""Спасибо, что вы выбрали {excursion_name} в составе {people_count} человек на {date}.

Поделитесь своими данными и один из наших менеджеров свяжется с вами, чтобы обсудить детали."""


def get_companions_created_text(excursion_name: str, date: str, people_count: int) -> str:
    """Текст при создании заявки на поиск попутчиков"""
    return f"""Ваша заявка на поиск попутчиков для {excursion_name} на {date} в составе {people_count} человек создана!

Поделитесь своими данными и один из наших менеджеров свяжется с вами, чтобы обсудить детали."""