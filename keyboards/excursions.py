"""Клавиатуры для флоу экскурсий"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_excursion_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа экскурсии"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Групповые", callback_data="exc_type:group")],
        [InlineKeyboardButton(text="👤 Индивидуальные", callback_data="exc_type:private")],
        [InlineKeyboardButton(text="🔍 Поиск попутчиков", callback_data="exc_type:companions")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_island")]
    ])
    return keyboard


def get_group_excursion_keyboard(excursion_id: str, has_prev: bool, has_next: bool, current_date: str) -> InlineKeyboardMarkup:
    """Клавиатура для групповой экскурсии"""
    buttons = []
    
    # Кнопка присоединиться
    buttons.append([InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"exc_join:{excursion_id}")])
    
    # Навигация по датам
    nav_buttons = []
    if has_prev:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущий день", callback_data=f"exc_date:prev:{current_date}"))
    if has_next:
        nav_buttons.append(InlineKeyboardButton(text="Следующий день ➡️", callback_data=f"exc_date:next:{current_date}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_no_group_excursions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура когда нет групповых экскурсий"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Подать заявку на поиск попутчиков", callback_data="exc_type:companions")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_type")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_private_excursion_keyboard(excursion_id: str, current_index: int, total: int) -> InlineKeyboardMarkup:
    """Клавиатура для индивидуальной экскурсии"""
    buttons = []
    
    # Кнопка бронирования
    buttons.append([InlineKeyboardButton(text="✅ Забронировать", callback_data=f"exc_book:{excursion_id}")])
    
    # Навигация
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"exc_nav:prev:{current_index}"))
    if current_index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"exc_nav:next:{current_index}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", callback_data=f"exc_view:{excursion_id}")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_companions_list_keyboard(month: int, year: int) -> InlineKeyboardMarkup:
    """Клавиатура для списка попутчиков с навигацией по месяцам"""
    from datetime import datetime
    
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    buttons = []
    
    # Навигация по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    buttons.append([
        InlineKeyboardButton(text="⬅️", callback_data=f"comp_month:{prev_year}-{prev_month:02d}"),
        InlineKeyboardButton(text=f"{month_names[month-1]} {year}", callback_data="comp_month:ignore"),
        InlineKeyboardButton(text="➡️", callback_data=f"comp_month:{next_year}-{next_month:02d}")
    ])
    
    buttons.append([InlineKeyboardButton(text="➕ Создать свою заявку", callback_data="comp_create:start")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_type")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_companions_excursion_keyboard(excursion_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для экскурсии с поиском попутчиков"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Записаться", callback_data=f"comp_join:{excursion_id}")],
        [InlineKeyboardButton(text="➕ Создать свою заявку", callback_data="comp_create:start")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="comp_back:list")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_companions_create_agree_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура согласия с условиями поиска попутчиков"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен, продолжить", callback_data="comp_create:agree")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="comp_back:list")]
    ])
    return keyboard