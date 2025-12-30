"""Клавиатуры бота"""

from .reply import get_main_reply_keyboard

from .common import (
    get_main_menu_keyboard,
    get_menu_keyboard,
    get_support_keyboard,
    get_back_to_main_keyboard,
    get_search_category_keyboard
)

from .hotels import (
    get_islands_keyboard,
    get_all_locations_keyboard,
    get_criteria_keyboard,
    get_stars_keyboard,
    get_currency_keyboard,
    get_price_method_keyboard,
    get_price_range_keyboard,
    get_hotel_navigation_keyboard,
    get_hotel_rooms_keyboard,
    get_share_contact_keyboard,
    get_hotel_card_simple_keyboard,
    get_cards_pagination_keyboard,
    get_custom_price_input_keyboard
)

from .excursions import (
    get_excursion_type_keyboard,
    get_group_excursion_keyboard,
    get_no_group_excursions_keyboard,
    get_private_excursion_keyboard,
    get_companions_list_keyboard,
    get_companions_excursion_keyboard,
    get_companions_create_agree_keyboard,
    get_companions_select_excursion_keyboard,
    get_group_excursion_full_keyboard,
    get_action_choice_keyboard,
    get_group_month_excursion_detail_keyboard,
    get_month_excursions_list_keyboard,
    get_private_islands_keyboard
)

from .transfers import (
    get_transfer_navigation_keyboard,
    get_transfer_card_simple_keyboard,
    get_transfer_booking_keyboard,
    get_transfer_people_count_keyboard
)

__all__ = [
    # Reply
    'get_main_reply_keyboard',
    # Common
    'get_main_menu_keyboard',
    'get_menu_keyboard',
    'get_support_keyboard',
    'get_back_to_main_keyboard',
    'get_search_category_keyboard',
    # Hotels
    'get_islands_keyboard',
    'get_all_locations_keyboard',
    'get_criteria_keyboard',
    'get_stars_keyboard',
    'get_currency_keyboard',
    'get_price_method_keyboard',
    'get_price_range_keyboard',
    'get_hotel_navigation_keyboard',
    'get_hotel_rooms_keyboard',
    'get_share_contact_keyboard',
    'get_hotel_card_simple_keyboard',
    'get_cards_pagination_keyboard',
    'get_custom_price_input_keyboard',
    # Excursions
    'get_excursion_type_keyboard',
    'get_group_excursion_keyboard',
    'get_no_group_excursions_keyboard',
    'get_private_excursion_keyboard',
    'get_companions_list_keyboard',
    'get_companions_excursion_keyboard',
    'get_companions_create_agree_keyboard',
    'get_companions_select_excursion_keyboard',
    'get_group_excursion_full_keyboard',
    'get_action_choice_keyboard',
    'get_group_month_excursion_detail_keyboard',
    'get_month_excursions_list_keyboard',
    'get_private_islands_keyboard',
    # Transfers
    'get_transfer_navigation_keyboard',
    'get_transfer_card_simple_keyboard',
    'get_transfer_booking_keyboard',
    'get_transfer_people_count_keyboard'
]