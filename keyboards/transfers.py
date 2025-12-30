"""Клавиатуры для флоу трансферов"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_transfer_navigation_keyboard(current_index: int, total: int, transfer_id: str) -> InlineKeyboardMarkup:
    """Клавиатура навигации по трансферам"""
    buttons = []

    # Кнопка бронирования
    buttons.append([InlineKeyboardButton(text="✅ Забронировать", callback_data=f"transfer_book:{transfer_id}")])

    # Навигация
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущий", callback_data=f"transfer_nav:prev:{current_index}"))
    if current_index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Следующий ➡️", callback_data=f"transfer_nav:next:{current_index}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    # Дополнительные кнопки
    buttons.append([InlineKeyboardButton(text="📋 Показать все трансферы страницей", callback_data="transfers:show_all")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_transfer_card_simple_keyboard(transfer_id: str) -> InlineKeyboardMarkup:
    """Упрощенная клавиатура для массовых блоков трансферов (без кнопки 'Показать все')"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Забронировать", callback_data=f"transfer_book:{transfer_id}")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_transfer_booking_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения бронирования трансфера"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Добавить в заказ", callback_data="transfer:add_to_order")],
        [InlineKeyboardButton(text="✅ Забронировать сейчас", callback_data="transfer:book_now")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_transfer_people_count_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора количества людей для трансфера"""
    buttons = [
        [
            InlineKeyboardButton(text="1 человек", callback_data="transfer_people_count:1"),
            InlineKeyboardButton(text="2 человека", callback_data="transfer_people_count:2"),
            InlineKeyboardButton(text="3 человека", callback_data="transfer_people_count:3")
        ],
        [
            InlineKeyboardButton(text="4 человека", callback_data="transfer_people_count:4"),
            InlineKeyboardButton(text="5 человек", callback_data="transfer_people_count:5"),
            InlineKeyboardButton(text="6 человек", callback_data="transfer_people_count:6")
        ],
        [
            InlineKeyboardButton(text="7 человек", callback_data="transfer_people_count:7"),
            InlineKeyboardButton(text="8 человек", callback_data="transfer_people_count:8"),
            InlineKeyboardButton(text="9 человек", callback_data="transfer_people_count:9")
        ],
        [
            InlineKeyboardButton(text="10 и более", callback_data="transfer_people_count:10")
        ],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
