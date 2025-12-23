"""Общие клавиатуры - главное меню, навигация"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import COMPANY_LINKS


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню выбора услуг"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏨 1. Отели", callback_data="main:hotels")],
        [InlineKeyboardButton(text="🏝 2. Экскурсии", callback_data="main:excursions")],
        [InlineKeyboardButton(text="📦 3. Пакетные туры", callback_data="main:packages")],
        [InlineKeyboardButton(text="🚗 4. Трансферы", callback_data="main:transfers")],
        [InlineKeyboardButton(text="🛒 Мои заказы", callback_data="menu:orders")],
        [InlineKeyboardButton(text="👤 Мои данные", callback_data="menu:profile")]
    ])
    return keyboard


def get_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Меню' - показывает подменю"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="menu:orders")],
        [InlineKeyboardButton(text="🏢 О компании", url=COMPANY_LINKS["about"])],
        [InlineKeyboardButton(text="📞 Контакты", url=COMPANY_LINKS["contacts"])],
        [InlineKeyboardButton(text="⭐ Отзывы", url=COMPANY_LINKS["reviews"])],
        [
            InlineKeyboardButton(text="YouTube", url=COMPANY_LINKS["youtube"]),
            InlineKeyboardButton(text="RuTube", url=COMPANY_LINKS["rutube"])
        ],
        [InlineKeyboardButton(text="Instagram", url=COMPANY_LINKS["instagram"])],
        [InlineKeyboardButton(text="🏠 К выбору услуг", callback_data="back:main")]
    ])
    return keyboard


def get_support_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Поддержка' - связь с менеджерами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать менеджеру", url=COMPANY_LINKS["support"])],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Простая кнопка возврата в главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_search_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории поиска"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏨 Отели", callback_data="search:hotels")],
        [InlineKeyboardButton(text="🏝 Экскурсии", callback_data="search:excursions")],
        [InlineKeyboardButton(text="🚗 Трансферы", callback_data="search:transfers")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard