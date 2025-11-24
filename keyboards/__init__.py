"""Клавиатуры бота"""

from .reply import get_main_reply_keyboard

from .common import (
    get_main_menu_keyboard,
    get_menu_keyboard,
    get_support_keyboard,
    get_back_to_main_keyboard
)

from .hotels import (
    get_islands_keyboard,
    get_criteria_keyboard,
    get_stars_keyboard,
    get_currency_keyboard,
    get_price_method_keyboard,
    get_price_range_keyboard,
    get_hotel_navigation_keyboard,
    get_share_contact_keyboard
)

__all__ = [
    # Reply
    'get_main_reply_keyboard',
    # Common
    'get_main_menu_keyboard',
    'get_menu_keyboard',
    'get_support_keyboard',
    'get_back_to_main_keyboard',
    # Hotels
    'get_islands_keyboard',
    'get_criteria_keyboard',
    'get_stars_keyboard',
    'get_currency_keyboard',
    'get_price_method_keyboard',
    'get_price_range_keyboard',
    'get_hotel_navigation_keyboard',
    'get_share_contact_keyboard'
]