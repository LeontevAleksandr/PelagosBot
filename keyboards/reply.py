"""Постоянные клавиатуры (Reply Keyboard)"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Постоянная клавиатура снизу экрана
    [Меню] [Поиск] [Поддержка]
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Меню"),
                KeyboardButton(text="🔍 Поиск"),
                KeyboardButton(text="💬 Поддержка")
            ]
        ],
        resize_keyboard=True,
        persistent=True  # Клавиатура всегда видна
    )
    return keyboard