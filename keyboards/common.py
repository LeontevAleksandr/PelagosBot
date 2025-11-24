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
        [InlineKeyboardButton(text="➕ 5. Другое", callback_data="main:other")]
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
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
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