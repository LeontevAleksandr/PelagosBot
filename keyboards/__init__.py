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

from .excursions import (
    get_excursion_type_keyboard,
    get_group_excursion_keyboard,
    get_no_group_excursions_keyboard,
    get_private_excursion_keyboard,
    get_companions_list_keyboard,
    get_companions_excursion_keyboard,
    get_companions_create_agree_keyboard
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
    'get_share_contact_keyboard',
    # Excursions
    'get_excursion_type_keyboard',
    'get_group_excursion_keyboard',
    'get_no_group_excursions_keyboard',
    'get_private_excursion_keyboard',
    'get_companions_list_keyboard',
    'get_companions_excursion_keyboard',
    'get_companions_create_agree_keyboard'
]