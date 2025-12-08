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
    CONTACT_RECEIVED,
    get_hotels_list_text,
    get_hotel_list_item_text,
    get_hotel_rooms_text
)

from .excursions import (
    get_excursions_intro_text,
    EXCURSIONS_SELECT_TYPE,
    EXCURSIONS_GROUP_INTRO,
    EXCURSIONS_PRIVATE_INTRO,
    COMPANIONS_INTRO,
    COMPANIONS_HOW_IT_WORKS,
    COMPANIONS_SELECT_EXCURSION,
    COMPANIONS_SELECT_DATE,
    COMPANIONS_INPUT_PEOPLE,
    NO_EXCURSIONS_FOUND,
    get_group_excursion_card_text,
    get_private_excursion_card_text,
    get_companions_excursion_card_text,
    get_excursion_join_text,
    get_excursion_booking_text,
    get_companions_created_text
)

from .packages import (
    get_packages_intro_text,
    get_package_card_text,
    get_package_booking_text
)

from .transfers import (
    get_transfers_intro_text,
    get_transfer_card_text,
    get_transfer_booking_text
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
    'CONTACT_RECEIVED',
    'get_hotels_list_text',
    'get_hotel_list_item_text',
    'get_hotel_rooms_text',
    # Excursions
    'get_excursions_intro_text',
    'EXCURSIONS_SELECT_TYPE',
    'EXCURSIONS_GROUP_INTRO',
    'EXCURSIONS_PRIVATE_INTRO',
    'COMPANIONS_INTRO',
    'COMPANIONS_HOW_IT_WORKS',
    'COMPANIONS_SELECT_EXCURSION',
    'COMPANIONS_SELECT_DATE',
    'COMPANIONS_INPUT_PEOPLE',
    'NO_EXCURSIONS_FOUND',
    'get_group_excursion_card_text',
    'get_private_excursion_card_text',
    'get_companions_excursion_card_text',
    'get_excursion_join_text',
    'get_excursion_booking_text',
    'get_companions_created_text',
    # Packages
    'get_packages_intro_text',
    'get_package_card_text',
    'get_package_booking_text',
    # Transfers
    'get_transfers_intro_text',
    'get_transfer_card_text',
    'get_transfer_booking_text'
]