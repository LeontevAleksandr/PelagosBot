"""Тексты сообщений бота"""

from .common import (
    GREETING,
    get_main_menu_text,
    MENU_TEXT,
    ABOUT_TEXT,
    CONTACTS_TEXT,
    REVIEWS_TEXT,
    MY_ORDERS_TEXT,
    MY_ORDERS_EMPTY,
    SUPPORT_TEXT,
    SEARCH_TEXT
)

from .hotels import (
    get_hotels_intro_text,
    HOTELS_SELECT_CRITERIA,
    HOTELS_SELECT_STARS,
    HOTELS_SELECT_CURRENCY,
    HOTELS_SELECT_PRICE_METHOD,
    HOTELS_INPUT_CUSTOM_RANGE,
    HOTELS_SELECT_PRICE_RANGE,
    HOTELS_SELECT_CHECK_IN,
    HOTELS_SELECT_CHECK_OUT,
    HOTELS_INPUT_ROOM_COUNT,
    get_hotels_confirmation_text,
    get_hotel_card_text,
    get_booking_confirmation_text,
    CONTACT_RECEIVED
)

__all__ = [
    # Common
    'GREETING',
    'get_main_menu_text',
    'MENU_TEXT',
    'ABOUT_TEXT',
    'CONTACTS_TEXT',
    'REVIEWS_TEXT',
    'MY_ORDERS_TEXT',
    'MY_ORDERS_EMPTY',
    'SUPPORT_TEXT',
    'SEARCH_TEXT',
    # Hotels
    'get_hotels_intro_text',
    'HOTELS_SELECT_CRITERIA',
    'HOTELS_SELECT_STARS',
    'HOTELS_SELECT_CURRENCY',
    'HOTELS_SELECT_PRICE_METHOD',
    'HOTELS_INPUT_CUSTOM_RANGE',
    'HOTELS_SELECT_PRICE_RANGE',
    'HOTELS_SELECT_CHECK_IN',
    'HOTELS_SELECT_CHECK_OUT',
    'HOTELS_INPUT_ROOM_COUNT',
    'get_hotels_confirmation_text',
    'get_hotel_card_text',
    'get_booking_confirmation_text',
    'CONTACT_RECEIVED'
]