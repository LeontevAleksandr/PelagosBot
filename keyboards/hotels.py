"""Клавиатуры для флоу отелей"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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


def get_criteria_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора критерия (звездность или цена)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Звёздность", callback_data="criteria:stars")],
        [InlineKeyboardButton(text="💵 Цена", callback_data="criteria:price")],
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
        [InlineKeyboardButton(text="✍️ Ввести собственный диапазон", callback_data="price_method:custom")],
        [InlineKeyboardButton(text="📋 Выбрать диапазон из списка", callback_data="price_method:list")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="hotels:back_to_currency")]
    ])
    return keyboard


def get_price_range_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора диапазона цен из списка"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Меньше 50$", callback_data="price_range:0-50"),
            InlineKeyboardButton(text="50-75$", callback_data="price_range:50-75")
        ],
        [
            InlineKeyboardButton(text="76-100$", callback_data="price_range:76-100"),
            InlineKeyboardButton(text="101-125$", callback_data="price_range:101-125")
        ],
        [
            InlineKeyboardButton(text="126-150$", callback_data="price_range:126-150"),
            InlineKeyboardButton(text="151-175$", callback_data="price_range:151-175")
        ],
        [
            InlineKeyboardButton(text="176-200$", callback_data="price_range:176-200"),
            InlineKeyboardButton(text="201-250$", callback_data="price_range:201-250")
        ],
        [
            InlineKeyboardButton(text="251-500$", callback_data="price_range:251-500"),
            InlineKeyboardButton(text="Больше 500$", callback_data="price_range:500-1000")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="hotels:back_to_price_method")]
    ])
    return keyboard


def get_hotel_navigation_keyboard(current_index: int, total: int, hotel_id: str, rooms: list) -> InlineKeyboardMarkup:
    """Клавиатура навигации по отелям с кнопками бронирования"""
    buttons = []
    
    # Кнопки бронирования номеров (показываем только первые 6 для краткости)
    if rooms:
        for i, room in enumerate(rooms[:6]):
            buttons.append([InlineKeyboardButton(
                text=f"Бронировать {room['name']}",
                callback_data=f"book:{hotel_id}:{room['id']}"
            )])
    
    # Навигация
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущий", callback_data=f"hotel_nav:prev:{current_index}"))
    if current_index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Следующий ➡️", callback_data=f"hotel_nav:next:{current_index}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Дополнительные кнопки
    buttons.append([InlineKeyboardButton(text="🔍 Смотреть отель", callback_data=f"hotel_view:{hotel_id}")])
    buttons.append([InlineKeyboardButton(text="🔄 Изменить критерии", callback_data="hotels:change_criteria")])
    buttons.append([InlineKeyboardButton(text="📋 Показать все отели списком", callback_data="hotels:show_all")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_share_contact_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для запроса контакта"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Поделиться контактом", callback_data="share:contact")]
    ])
    return keyboard