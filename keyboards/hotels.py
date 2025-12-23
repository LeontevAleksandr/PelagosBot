"""Клавиатуры для флоу отелей"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import get_currency_symbol


def get_islands_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора островов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Боракай", callback_data="island:boracay"),
            InlineKeyboardButton(text="Себу", callback_data="island:cebu")
        ],
        [
            InlineKeyboardButton(text="Манила", callback_data="island:manila"),
            InlineKeyboardButton(text="Бохоль", callback_data="island:bohol")
        ],
        [InlineKeyboardButton(text="Палаван", callback_data="island:palawan")],
        [InlineKeyboardButton(text="Другие острова", callback_data="island:other")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_all_locations_keyboard(locations: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора локации из полного списка с пагинацией

    Args:
        locations: список локаций [{id, name, code, parent}, ...]
        page: текущая страница (0-based)
        per_page: количество локаций на странице
    """
    # Находим The Philippines (корневой регион)
    philippines = next((loc for loc in locations if loc.get('parent') == 0), None)

    if philippines:
        # Фильтруем только дочерние острова от The Philippines
        # Это будут конкретные острова: Boracay, Manila, Cebu и т.д.
        island_locations = [loc for loc in locations if loc.get('parent') == philippines['id']]
    else:
        # Fallback: если не найден The Philippines, берем все с parent != 0
        island_locations = [loc for loc in locations if loc.get('parent') and loc.get('parent') != 0]

    # Сортируем по имени
    island_locations = sorted(island_locations, key=lambda x: x.get('name', ''))

    # Пагинация
    total = len(island_locations)
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_locations = island_locations[start_idx:end_idx]

    buttons = []

    # Кнопки локаций (по 2 в ряд)
    for i in range(0, len(page_locations), 2):
        row = []
        loc1 = page_locations[i]
        row.append(InlineKeyboardButton(
            text=loc1['name'][:30],  # Обрезаем длинные названия
            callback_data=f"location:{loc1['code']}"
        ))

        if i + 1 < len(page_locations):
            loc2 = page_locations[i + 1]
            row.append(InlineKeyboardButton(
                text=loc2['name'][:30],
                callback_data=f"location:{loc2['code']}"
            ))

        buttons.append(row)

    # Навигация по страницам
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"locations_page:{page - 1}"))

        nav_buttons.append(InlineKeyboardButton(
            text=f"· {page + 1}/{total_pages} ·",
            callback_data="locations_page:current"
        ))

        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"locations_page:{page + 1}"))

        buttons.append(nav_buttons)

    # Кнопка назад
    buttons.append([InlineKeyboardButton(text="🔙 Назад к основным островам", callback_data="hotels:back_to_island")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_criteria_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора критерия (звездность или цена)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Звёздность", callback_data="criteria:stars")],
        [InlineKeyboardButton(text="💵 Цена", callback_data="criteria:price")],
        [InlineKeyboardButton(text="🏨 Хочу посмотреть все!", callback_data="criteria:all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="hotels:back_to_island")]
    ])
    return keyboard


def get_stars_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора звездности"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐⭐ 2 звезды", callback_data="stars:2")],
        [InlineKeyboardButton(text="⭐⭐⭐ 3 звезды", callback_data="stars:3")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐ 4 звезды", callback_data="stars:4")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐⭐ 5 звёзд", callback_data="stars:5")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="hotels:back_to_criteria")]
    ])
    return keyboard


def get_currency_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора валюты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="₽ Рубль", callback_data="currency:rub"),
            InlineKeyboardButton(text="$ Доллар", callback_data="currency:usd"),
            InlineKeyboardButton(text="₱ Песо", callback_data="currency:peso")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="hotels:back_to_criteria")]
    ])
    return keyboard


def get_price_method_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора метода ввода цены"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ввести диапазон", callback_data="price_method:custom")],
        [InlineKeyboardButton(text="📋 Выбрать диапазон", callback_data="price_method:list")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="hotels:back_to_currency")]
    ])
    return keyboard


def get_price_range_keyboard(currency: str = "usd") -> InlineKeyboardMarkup:
    """Клавиатура выбора диапазона цен из списка с учетом валюты"""

    symbol = get_currency_symbol(currency)

    # Базовые диапазоны в USD
    if currency == "usd":
        ranges = [
            ("Меньше 50$", "0-50"),
            ("50-75$", "50-75"),
            ("76-100$", "76-100"),
            ("101-125$", "101-125"),
            ("126-150$", "126-150"),
            ("151-175$", "151-175"),
            ("176-200$", "176-200"),
            ("201-250$", "201-250"),
            ("251-500$", "251-500"),
            ("Больше 500$", "500-1000")
        ]
    elif currency == "rub":
        # Диапазоны для рублей (примерно от 4000 до 40000)
        ranges = [
            (f"Меньше 4000{symbol}", "0-4000"),
            (f"4000-6000{symbol}", "4000-6000"),
            (f"6000-8000{symbol}", "6000-8000"),
            (f"8000-10000{symbol}", "8000-10000"),
            (f"10000-12000{symbol}", "10000-12000"),
            (f"12000-15000{symbol}", "12000-15000"),
            (f"15000-18000{symbol}", "15000-18000"),
            (f"18000-22000{symbol}", "18000-22000"),
            (f"22000-30000{symbol}", "22000-30000"),
            (f"Больше 30000{symbol}", "30000-40000")
        ]
    else:  # peso
        # Диапазоны для песо (примерно от 3000 до 30000)
        ranges = [
            (f"Меньше 3000{symbol}", "0-3000"),
            (f"3000-4500{symbol}", "3000-4500"),
            (f"4500-6000{symbol}", "4500-6000"),
            (f"6000-7500{symbol}", "6000-7500"),
            (f"7500-9000{symbol}", "7500-9000"),
            (f"9000-10500{symbol}", "9000-10500"),
            (f"10500-12000{symbol}", "10500-12000"),
            (f"12000-15000{symbol}", "12000-15000"),
            (f"15000-20000{symbol}", "15000-20000"),
            (f"Больше 20000{symbol}", "20000-30000")
        ]

    # Формируем кнопки по 2 в ряд
    buttons = []
    for i in range(0, len(ranges), 2):
        row = []
        row.append(InlineKeyboardButton(text=ranges[i][0], callback_data=f"price_range:{ranges[i][1]}:{currency}"))
        if i + 1 < len(ranges):
            row.append(InlineKeyboardButton(text=ranges[i+1][0], callback_data=f"price_range:{ranges[i+1][1]}:{currency}"))
        buttons.append(row)

    # Кнопка назад
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="hotels:back_to_price_method")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_hotel_navigation_keyboard(current_index: int, total: int, hotel_id: str) -> InlineKeyboardMarkup:
    """Клавиатура навигации по отелям"""
    buttons = []

    # Навигация
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущий", callback_data=f"hotel_nav:prev:{current_index}"))
    if current_index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Следующий ➡️", callback_data=f"hotel_nav:next:{current_index}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    # Дополнительные кнопки
    buttons.append([
        InlineKeyboardButton(text="🔍 Смотреть номера", callback_data=f"hotel_view:{hotel_id}"),
        InlineKeyboardButton(text="🔄 Изменить критерии", callback_data="hotels:change_criteria")
    ])
    buttons.append([InlineKeyboardButton(text="📋 Показать все отели списком", callback_data="hotels:show_all_list")])
    buttons.append([InlineKeyboardButton(text="📋 Показать все отели страницей", callback_data="hotels:show_all")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_hotel_rooms_keyboard(hotel_id: str, rooms: list) -> InlineKeyboardMarkup:
    """Клавиатура с кнопками бронирования для каждого номера"""
    buttons = []

    # Кнопки бронирования номеров
    for room in rooms:
        buttons.append([InlineKeyboardButton(
            text=f"{room['name']}",
            callback_data=f"book:{hotel_id}:{room['id']}"
        )])

    # Кнопка назад
    buttons.append([InlineKeyboardButton(text="🔙 Назад к отелю", callback_data=f"hotel_back:{hotel_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_hotel_card_simple_keyboard(hotel_id: str) -> InlineKeyboardMarkup:
    """Упрощенная клавиатура для массовых блоков отелей (без кнопки 'Показать все')"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Смотреть номера", callback_data=f"hotel_view:{hotel_id}"),
            InlineKeyboardButton(text="🔄 Изменить критерии", callback_data="hotels:change_criteria")
        ],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_cards_pagination_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура-контроллер для пагинации массовых блоков"""
    buttons = []

    # Навигация по страницам
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"cards_page:{current_page - 1}"))

    # Кнопки номеров страниц (показываем до 5 страниц)
    page_buttons = []
    start_page = max(1, current_page - 2)
    end_page = min(total_pages, start_page + 4)

    for page in range(start_page, end_page + 1):
        if page == current_page:
            page_buttons.append(InlineKeyboardButton(text=f"· {page} ·", callback_data="current_page"))
        else:
            page_buttons.append(InlineKeyboardButton(text=str(page), callback_data=f"cards_page:{page}"))

    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"cards_page:{current_page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)
    if page_buttons:
        buttons.append(page_buttons)

    # Дополнительные кнопки
    buttons.append([
        InlineKeyboardButton(text="🔄 Изменить критерии", callback_data="hotels:change_criteria"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_custom_price_input_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ввода пользовательского диапазона цен"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="hotels:back_to_price_method")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_share_contact_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для запроса контакта"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Поделиться контактом", callback_data="share:contact")]
    ])
    return keyboard