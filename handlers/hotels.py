"""Обработчики флоу отелей"""
import asyncio
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

from handlers.main_menu import show_main_menu

logger = logging.getLogger(__name__)

from states.user_states import UserStates
from keyboards import (
    get_islands_keyboard,
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
    get_back_to_main_keyboard,
    get_custom_price_input_keyboard,
    get_all_locations_keyboard
)
from utils.texts import (
    get_hotels_intro_text,
    HOTELS_SELECT_CRITERIA,
    HOTELS_SELECT_STARS,
    HOTELS_SELECT_CURRENCY,
    HOTELS_SELECT_PRICE_METHOD,
    get_hotels_input_custom_range_text,
    HOTELS_SELECT_PRICE_RANGE,
    HOTELS_SELECT_CHECK_IN,
    HOTELS_SELECT_CHECK_OUT,
    get_hotels_confirmation_text,
    get_hotel_card_text,
    HOTELS_INPUT_ROOM_COUNT,
    get_booking_confirmation_text,
    CONTACT_RECEIVED,
    get_hotels_list_text,
    get_hotel_list_item_text,
    get_hotel_rooms_text
)

from utils.preloader import get_preloader

from utils.helpers import (
    validate_price_range,
    get_calendar_keyboard,
    get_island_name_ru,
    format_date,
    get_currency_symbol,
    convert_price,
    validate_phone_number,
    show_loading_message,
    delete_loading_message,
    get_exchange_rates
)
from utils.data_loader import get_data_loader
from utils.contact_handler import contact_handler
from utils.order_manager import order_manager

router = Router()


# ========== Вспомогательные функции ==========

async def _preload_hotel_rooms(hotel: dict, state_data: dict):
    """Фоновая предзагрузка номеров и цен отеля"""
    try:
        hotel_with_rooms = await get_data_loader().get_hotel_by_id(
            int(hotel['id']),
            location_code=state_data.get('search_island'),
            check_in=state_data.get('check_in'),
            check_out=state_data.get('check_out')
        )
        if hotel_with_rooms:
            hotel['rooms'] = hotel_with_rooms.get('rooms', [])
            prices_count = len([r for r in hotel['rooms'] if r.get('price', 0) > 0])
            logger.info(f"✅ Предзагружено {len(hotel['rooms'])} номеров ({prices_count} с ценами) для отеля {hotel['id']}")
    except Exception as e:
        logger.debug(f"⚠️ Ошибка предзагрузки отеля {hotel.get('id')}: {e}")


# ========== Старт флоу отелей ==========

@router.callback_query(F.data == "main:hotels")
async def start_hotels_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу отелей - вступительное сообщение"""
    await callback.answer()
    
    hotels_count = 200
    
    await callback.message.edit_text(
        get_hotels_intro_text(hotels_count),
        reply_markup=get_islands_keyboard(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_ISLAND)


# ========== Выбор острова ==========

@router.callback_query(UserStates.HOTELS_SELECT_ISLAND, F.data.startswith("island:"))
async def select_island(callback: CallbackQuery, state: FSMContext):
    """Выбор острова"""
    await callback.answer()

    island_code = callback.data.split(":")[1]

    if island_code == "other":
        # Показываем все доступные локации из API
        loading_msg = await callback.message.edit_text("⏳ Загружаю список всех доступных островов...")

        try:
            locations = await get_data_loader().get_all_locations()

            if not locations:
                await loading_msg.edit_text(
                    "😔 К сожалению, не удалось загрузить список островов. Попробуйте позже.",
                    reply_markup=get_back_to_main_keyboard()
                )
                return

            # Сохраняем список локаций в состоянии
            await state.update_data(all_locations=locations, locations_page=0)

            # Находим The Philippines для подсчета островов
            philippines = next((loc for loc in locations if loc.get('parent') == 0), None)
            if philippines:
                islands_count = len([l for l in locations if l.get('parent') == philippines['id']])
            else:
                islands_count = len([l for l in locations if l.get('parent') and l.get('parent') != 0])

            await loading_msg.edit_text(
                f"🏝 **Доступные острова Филиппин** ({islands_count} островов)\n\n"
                "Выберите остров из списка:",
                reply_markup=get_all_locations_keyboard(locations, page=0),
                parse_mode="Markdown"
            )

            await state.set_state(UserStates.HOTELS_SELECT_OTHER_LOCATION)

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки локаций: {e}")
            await loading_msg.edit_text(
                "😔 Произошла ошибка при загрузке списка островов.",
                reply_markup=get_back_to_main_keyboard()
            )
        return

    # Сохраняем остров
    await state.update_data(island=island_code)

    await callback.message.edit_text(
        HOTELS_SELECT_CRITERIA,
        reply_markup=get_criteria_keyboard()
    )

    await state.set_state(UserStates.HOTELS_SELECT_CRITERIA)


# ========== Обработчики для "Других островов" ==========

@router.callback_query(UserStates.HOTELS_SELECT_OTHER_LOCATION, F.data.startswith("location:"))
async def select_other_location(callback: CallbackQuery, state: FSMContext):
    """Выбор локации из полного списка"""
    await callback.answer()

    location_code = callback.data.split(":")[1]

    # Сохраняем выбранную локацию
    await state.update_data(island=location_code)

    await callback.message.edit_text(
        HOTELS_SELECT_CRITERIA,
        reply_markup=get_criteria_keyboard()
    )

    await state.set_state(UserStates.HOTELS_SELECT_CRITERIA)


@router.callback_query(UserStates.HOTELS_SELECT_OTHER_LOCATION, F.data.startswith("locations_page:"))
async def navigate_locations_page(callback: CallbackQuery, state: FSMContext):
    """Навигация по страницам локаций"""
    await callback.answer()

    page_data = callback.data.split(":")[1]

    if page_data == "current":
        return  # Игнорируем клик на текущую страницу

    page = int(page_data)

    # Получаем сохраненные локации
    data = await state.get_data()
    locations = data.get('all_locations', [])

    if not locations:
        await callback.answer("Ошибка: список локаций не найден", show_alert=True)
        return

    # Обновляем страницу
    await state.update_data(locations_page=page)

    # Находим The Philippines для подсчета островов
    philippines = next((loc for loc in locations if loc.get('parent') == 0), None)
    if philippines:
        islands_count = len([l for l in locations if l.get('parent') == philippines['id']])
    else:
        islands_count = len([l for l in locations if l.get('parent') and l.get('parent') != 0])

    await callback.message.edit_text(
        f"🏝 **Доступные острова Филиппин** ({islands_count} островов)\n\n"
        "Выберите остров из списка:",
        reply_markup=get_all_locations_keyboard(locations, page=page),
        parse_mode="Markdown"
    )


# ========== Выбор критерия ==========

@router.callback_query(UserStates.HOTELS_SELECT_CRITERIA, F.data == "criteria:stars")
async def select_criteria_stars(callback: CallbackQuery, state: FSMContext):
    """Выбран критерий - звездность"""
    await callback.answer()
    
    await state.update_data(criteria="stars", stars=None, price_range=None)
    
    await callback.message.edit_text(
        HOTELS_SELECT_STARS,
        reply_markup=get_stars_keyboard()
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_STARS)


@router.callback_query(UserStates.HOTELS_SELECT_CRITERIA, F.data == "criteria:price")
async def select_criteria_price(callback: CallbackQuery, state: FSMContext):
    """Выбран критерий - цена"""
    await callback.answer()

    await state.update_data(criteria="price", stars=None)

    await callback.message.edit_text(
        HOTELS_SELECT_CURRENCY,
        reply_markup=get_currency_keyboard()
    )

    await state.set_state(UserStates.HOTELS_SELECT_CURRENCY)


@router.callback_query(UserStates.HOTELS_SELECT_CRITERIA, F.data == "criteria:all")
async def select_criteria_all(callback: CallbackQuery, state: FSMContext):
    """Выбран критерий - показать все отели"""
    await callback.answer()

    await state.update_data(criteria="all", stars=None, price_range=None, min_price=None, max_price=None)

    # Сразу переходим к выбору дат
    await show_check_in_calendar(callback.message, state)


# ========== Ветка A: Звездность ==========

@router.callback_query(UserStates.HOTELS_SELECT_STARS, F.data.startswith("stars:"))
async def select_stars(callback: CallbackQuery, state: FSMContext):
    """Выбор звездности"""
    await callback.answer()
    
    stars = int(callback.data.split(":")[1])
    await state.update_data(stars=stars)
    
    # Переходим к выбору дат
    await show_check_in_calendar(callback.message, state)


# ========== Ветка B: Цена ==========

@router.callback_query(UserStates.HOTELS_SELECT_CURRENCY, F.data.startswith("currency:"))
async def select_currency(callback: CallbackQuery, state: FSMContext):
    """Выбор валюты"""
    await callback.answer()
    
    currency = callback.data.split(":")[1]
    await state.update_data(currency=currency)
    
    await callback.message.edit_text(
        HOTELS_SELECT_PRICE_METHOD,
        reply_markup=get_price_method_keyboard()
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_PRICE_METHOD)


@router.callback_query(UserStates.HOTELS_SELECT_PRICE_METHOD, F.data == "price_method:custom")
async def select_price_method_custom(callback: CallbackQuery, state: FSMContext):
    """Выбран метод - собственный диапазон"""
    await callback.answer()

    # Получаем выбранную валюту
    data = await state.get_data()
    currency = data.get("currency", "usd")

    await callback.message.edit_text(
        get_hotels_input_custom_range_text(currency),
        reply_markup=get_custom_price_input_keyboard()
    )

    await state.set_state(UserStates.HOTELS_INPUT_CUSTOM_RANGE)


@router.callback_query(UserStates.HOTELS_SELECT_PRICE_METHOD, F.data == "price_method:list")
async def select_price_method_list(callback: CallbackQuery, state: FSMContext):
    """Выбран метод - диапазон из списка"""
    await callback.answer()

    # Получаем выбранную валюту
    data = await state.get_data()
    currency = data.get("currency", "usd")

    await callback.message.edit_text(
        HOTELS_SELECT_PRICE_RANGE,
        reply_markup=get_price_range_keyboard(currency)
    )

    await state.set_state(UserStates.HOTELS_SELECT_PRICE_RANGE)


@router.message(UserStates.HOTELS_INPUT_CUSTOM_RANGE, F.text)
async def process_custom_price_range(message: Message, state: FSMContext):
    """Обработка ввода собственного диапазона"""
    # Получаем выбранную валюту
    data = await state.get_data()
    currency = data.get("currency", "usd")

    # Валидируем с учетом валюты
    valid, min_price, max_price = validate_price_range(message.text, currency)

    if not valid:
        # Получаем лимиты для сообщения об ошибке
        rates = get_exchange_rates()
        symbol = get_currency_symbol(currency)
        min_limit = int(5 * rates[currency])
        max_limit = int(1000 * rates[currency])

        await message.answer(
            f"❌ Неверный формат! Пожалуйста, введите диапазон в формате: {min_limit}-{max_limit}{symbol}",
            reply_markup=get_custom_price_input_keyboard()
        )
        return

    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    # Конвертируем цены в USD для фильтрации (т.к. цены в БД в USD)
    if currency != "usd":
        min_price_usd = int(convert_price(min_price, currency, "usd"))
        max_price_usd = int(convert_price(max_price, currency, "usd"))
    else:
        min_price_usd = min_price
        max_price_usd = max_price

    await state.update_data(
        price_range=f"{min_price}-{max_price}",
        min_price=min_price_usd,
        max_price=max_price_usd,
        display_currency=currency  # Сохраняем валюту для отображения
    )

    # Переходим к выбору дат
    await show_check_in_calendar(message, state, use_answer=True)


@router.callback_query(UserStates.HOTELS_SELECT_PRICE_RANGE, F.data.startswith("price_range:"))
async def select_price_range(callback: CallbackQuery, state: FSMContext):
    """Выбор диапазона из списка"""
    await callback.answer()

    # Парсим данные: price_range:min-max:currency
    parts = callback.data.split(":")
    price_range = parts[1]
    currency = parts[2] if len(parts) > 2 else "usd"

    min_price, max_price = map(int, price_range.split("-"))

    # Конвертируем в USD для фильтрации (т.к. цены в БД в USD)
    if currency != "usd":
        min_price_usd = int(convert_price(min_price, currency, "usd"))
        max_price_usd = int(convert_price(max_price, currency, "usd"))
    else:
        min_price_usd = min_price
        max_price_usd = max_price

    await state.update_data(
        price_range=price_range,
        min_price=min_price_usd,
        max_price=max_price_usd,
        display_currency=currency  # Сохраняем валюту для отображения
    )

    # Переходим к выбору дат
    await show_check_in_calendar(callback.message, state)


# ========== Календарь и даты ==========

async def show_check_in_calendar(message: Message, state: FSMContext, use_answer: bool = False):
    """Показать календарь выбора даты заезда

    Args:
        message: Сообщение для отправки календаря
        state: Контекст FSM
        use_answer: Если True, использует answer вместо edit_text
    """
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month)

    if use_answer:
        await message.answer(
            HOTELS_SELECT_CHECK_IN,
            reply_markup=calendar
        )
    else:
        await message.edit_text(
            HOTELS_SELECT_CHECK_IN,
            reply_markup=calendar
        )

    await state.set_state(UserStates.HOTELS_SELECT_CHECK_IN)


@router.callback_query(UserStates.HOTELS_SELECT_CHECK_IN, F.data.startswith("cal:"))
async def navigate_check_in_calendar(callback: CallbackQuery, state: FSMContext):
    """Навигация по календарю заезда"""
    await callback.answer()
    
    date_str = callback.data.split(":")[1]
    
    if date_str == "ignore":
        return
    
    # Переключение месяца
    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month)
    
    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.HOTELS_SELECT_CHECK_IN, F.data.startswith("date:"))
async def select_check_in_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты заезда"""
    await callback.answer()
    
    check_in = callback.data.split(":")[1]
    await state.update_data(check_in=check_in)
    
    # Показываем календарь выезда
    date_obj = datetime.strptime(check_in, "%Y-%m-%d")
    calendar = get_calendar_keyboard(date_obj.year, date_obj.month, selected_date=check_in)
    
    await callback.message.edit_text(
        HOTELS_SELECT_CHECK_OUT,
        reply_markup=calendar
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_CHECK_OUT)


@router.callback_query(UserStates.HOTELS_SELECT_CHECK_OUT, F.data.startswith("cal:"))
async def navigate_check_out_calendar(callback: CallbackQuery, state: FSMContext):
    """Навигация по календарю выезда"""
    await callback.answer()
    
    date_str = callback.data.split(":")[1]
    
    if date_str == "ignore":
        return
    
    data = await state.get_data()
    check_in = data.get("check_in")
    
    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month, selected_date=check_in)
    
    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.HOTELS_SELECT_CHECK_OUT, F.data.startswith("date:"))
async def select_check_out_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты выезда"""
    await callback.answer()

    check_out = callback.data.split(":")[1]
    logger.info(f"📅 Выбрана дата выезда: {check_out}")
    await state.update_data(check_out=check_out)

    # Показываем подтверждение и результаты
    logger.info("🔍 Начинаем поиск отелей...")
    await show_hotels_results(callback.message, state)


# ========== Показ результатов ==========

async def show_hotels_results(message: Message, state: FSMContext):
    """Показать результаты поиска отелей"""
    data = await state.get_data()

    user_name = data.get("user_name", "Друг")
    island = data.get("island")
    stars = data.get("stars")
    price_range = data.get("price_range", "Не указана")
    check_in = format_date(data.get("check_in"))
    check_out = format_date(data.get("check_out"))
    min_price = data.get("min_price")
    max_price = data.get("max_price")

    logger.info(f"🏝️ Фильтры: island={island}, stars={stars}, price={min_price}-{max_price}")

    # Показываем сообщение о загрузке
    loading_msg = await show_loading_message(message, "⏳ Загружаю отели...")

    # Получаем отели (первый загружается с ценами, остальные 14 параллельно, остальные без цен)
    logger.info("📡 Запрос отелей из API...")
    result = await get_data_loader().get_hotels_by_filters(
        island=island,
        stars=stars,
        min_price=min_price,
        max_price=max_price,
        check_in=data.get("check_in"),
        check_out=data.get("check_out")
    )

    hotels = result['hotels']
    total = result['total']
    logger.info(f"✅ Получено отелей: {len(hotels)} (всего найдено: {total})")

    # Удаляем сообщение о загрузке
    await delete_loading_message(loading_msg)

    if not hotels:
        logger.warning("❌ Отели не найдены по заданным критериям")
        await message.edit_text(
            f"😔 К сожалению, по вашим критериям отели не найдены.\n\nПопробуйте изменить параметры поиска.",
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Сохраняем отели, индекс и фильтры для дозагрузки
    logger.info(f"💾 Сохраняем {len(hotels)} отелей в state")
    await state.update_data(
        hotels=hotels,
        current_hotel_index=0,
        total_hotels=total,
        # Сохраняем фильтры для дозагрузки номеров при навигации
        search_island=island,
        search_stars=stars
    )

    # Показываем подтверждение
    logger.info("📝 Формируем текст подтверждения...")
    confirmation_text = get_hotels_confirmation_text(
        user_name,
        get_island_name_ru(island),
        f"{stars} звезд" if stars else "Не указана",
        price_range,
        check_in,
        check_out
    )

    logger.info("✏️ Редактируем сообщение с подтверждением...")
    await message.edit_text(confirmation_text)

    # Показываем первый отель
    logger.info("🏨 Показываем первую карточку отеля...")
    await show_hotel_card(message, state, 0)

    await state.set_state(UserStates.HOTELS_SHOW_RESULTS)
    logger.info("✅ show_hotels_results завершена успешно!")


async def show_hotel_card(message: Message, state: FSMContext, index: int):
    """Показать карточку отеля"""
    data = await state.get_data()
    hotels = data.get("hotels", [])

    if index < 0 or index >= len(hotels):
        return

    hotel = hotels[index]

    # Получаем номера отеля (если ещё не загружены - загружаем)
    rooms = hotel.get("rooms", [])
    loading_msg = None
    if not rooms:
        logger.info(f"⚡ Дозагрузка номеров для отеля {hotel['id']}")
        # Показываем сообщение о загрузке
        loading_msg = await show_loading_message(message, "⏳ Загружаю информацию о номерах...")
        try:
            # Получаем location_code и даты из состояния
            search_island = data.get('search_island')
            check_in = data.get('check_in')
            check_out = data.get('check_out')
            # Загружаем номера для этого отеля с актуальными ценами
            hotel_with_rooms = await get_data_loader().get_hotel_by_id(
                int(hotel['id']),
                location_code=search_island,
                check_in=check_in,
                check_out=check_out
            )
            if hotel_with_rooms:
                rooms = hotel_with_rooms.get("rooms", [])
                # Обновляем отель в списке
                hotel['rooms'] = rooms
                hotels[index] = hotel
                await state.update_data(hotels=hotels)
                logger.info(f"   ✓ Загружено {len(rooms)} номеров")
        except Exception as e:
            logger.error(f"   ❌ Ошибка загрузки номеров: {e}")
            rooms = []
        finally:
            # Удаляем сообщение о загрузке
            if loading_msg:
                await delete_loading_message(loading_msg)

    # Запускаем предзагрузку следующего отеля в фоне
    if index + 1 < len(hotels):
        next_hotel = hotels[index + 1]
        if not next_hotel.get("rooms"):
            asyncio.create_task(_preload_hotel_rooms(next_hotel, data))

    # Формируем текст карточки
    card_text = get_hotel_card_text(hotel, rooms)

    # Формируем клавиатуру
    keyboard = get_hotel_navigation_keyboard(
        current_index=index,
        total=len(hotels),
        hotel_id=hotel["id"]
    )

    # Получаем URL фото из данных отеля
    photo_url = hotel.get("photo")

    if photo_url:
        # Отправляем с фото
        await message.answer_photo(
            photo=photo_url,
            caption=card_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        # Отправляем без фото
        await message.answer(
            card_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


async def send_hotels_cards_page(message: Message, state: FSMContext, page: int):
    """
    Отправить страницу с отелями блоками (использует API пагинацию)

    Args:
        page: номер страницы (1-based для пользователя)
    """
    data = await state.get_data()
    search_island = data.get('search_island')
    stars = data.get('stars')
    min_price = data.get('min_price')
    max_price = data.get('max_price')

    if not search_island:
        return

    # Показываем сообщение о загрузке
    loading_msg = await show_loading_message(message, "⏳ Загружаю отели...")

    # Загружаем страницу через API (page - 1 потому что API использует 0-based)
    result = await get_data_loader().get_hotels_by_filters(
        island=search_island,
        stars=stars,
        min_price=min_price,
        max_price=max_price,
        page=page - 1,  # Конвертируем в 0-based для API
        per_page=5,
        check_in=data.get("check_in"),
        check_out=data.get("check_out")
    )

    hotels = result['hotels']
    total_pages = result['total_pages']

    # Удаляем сообщение о загрузке
    await delete_loading_message(loading_msg)

    # Запускаем предзагрузку следующей страницы в фоне
    preloader = get_preloader()
    if preloader and page < total_pages:
        preloader.preload_next(
            island=search_island,
            stars=stars,
            current_page=page + 1,
            check_in=data.get("check_in"),
            check_out=data.get("check_out")
        )

    if not hotels:
        await message.answer("❌ На этой странице нет отелей")
        return

    # Функция форматирования карточки
    def format_card(hotel):
        rooms = hotel.get("rooms", [])
        return get_hotel_card_text(hotel, rooms)

    # Функция создания клавиатуры
    def get_keyboard(hotel):
        return get_hotel_card_simple_keyboard(hotel["id"])

    # Отправляем карточки отелей
    for hotel in hotels:
        card_text = format_card(hotel)
        keyboard = get_keyboard(hotel)
        photo_url = hotel.get("photo")

        try:
            if photo_url:
                await message.answer_photo(
                    photo=photo_url,
                    caption=card_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    card_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.error(f"Ошибка при отправке карточки: {e}")
            continue

    # Формируем клавиатуру навигации
    nav_buttons = []

    # Кнопка "Назад"
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"cards_page:{page - 1}"
        ))

    # Кнопки страниц
    page_buttons = []
    start_page = max(1, page - 2)
    end_page = min(total_pages, start_page + 5)

    for p in range(start_page, end_page + 1):
        if p == page:
            page_buttons.append(InlineKeyboardButton(
                text=f"• {p} •",
                callback_data=f"cards_page:{p}"
            ))
        else:
            page_buttons.append(InlineKeyboardButton(
                text=str(p),
                callback_data=f"cards_page:{p}"
            ))

    # Кнопка "Вперед"
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"cards_page:{page + 1}"
        ))

    # Формируем итоговую клавиатуру
    control_buttons = []
    if nav_buttons:
        control_buttons.append(nav_buttons)
    if page_buttons:
        control_buttons.append(page_buttons)

    control_buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    control_keyboard = InlineKeyboardMarkup(inline_keyboard=control_buttons)

    await message.answer(
        f"📋 Страница {page} из {total_pages}",
        reply_markup=control_keyboard,
        parse_mode="Markdown"
    )


# ========== Навигация по отелям ==========

@router.callback_query(UserStates.HOTELS_SHOW_RESULTS, F.data.startswith("hotel_nav:"))
async def navigate_hotels(callback: CallbackQuery, state: FSMContext):
    """Навигация по списку отелей"""
    await callback.answer()
    
    parts = callback.data.split(":")
    direction = parts[1]  # prev или next
    current_index = int(parts[2])
    
    if direction == "prev":
        new_index = current_index - 1
    else:
        new_index = current_index + 1
    
    await state.update_data(current_hotel_index=new_index)
    
    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем новую карточку
    await show_hotel_card(callback.message, state, new_index)


# ========== Бронирование ==========

@router.callback_query(UserStates.HOTELS_SHOW_RESULTS, F.data.startswith("book:"))
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начало бронирования номера"""
    await callback.answer()
    
    parts = callback.data.split(":")
    hotel_id = parts[1]
    room_id = parts[2]
    
    await state.update_data(selected_hotel_id=hotel_id, selected_room_id=room_id)
    
    await callback.message.answer(
        HOTELS_INPUT_ROOM_COUNT,
        reply_markup=get_back_to_main_keyboard()
    )
    
    await state.set_state(UserStates.HOTELS_INPUT_ROOM_COUNT)


@router.message(UserStates.HOTELS_INPUT_ROOM_COUNT, F.text)
async def process_room_count(message: Message, state: FSMContext):
    """Обработка количества номеров"""
    try:
        room_count = int(message.text.strip())
        
        if room_count < 1:
            raise ValueError
        
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        data = await state.get_data()
        hotel_id = data.get("selected_hotel_id")
        room_id = data.get("selected_room_id")
        check_in_raw = data.get("check_in")  # YYYY-MM-DD формат
        check_out_raw = data.get("check_out")  # YYYY-MM-DD формат
        check_in = format_date(check_in_raw)  # Форматированная дата для отображения
        check_out = format_date(check_out_raw)  # Форматированная дата для отображения
        search_island = data.get("search_island")

        hotel = await get_data_loader().get_hotel_by_id(
            int(hotel_id),
            location_code=search_island,
            check_in=check_in_raw,
            check_out=check_out_raw
        )
        room = await get_data_loader().get_room_by_id(int(hotel_id), int(room_id))

        # Сохраняем количество комнат
        await state.update_data(room_count=room_count)

        # Показываем подтверждение с двумя кнопками
        confirmation_text = get_booking_confirmation_text(
            room_count,
            room["name"],
            hotel["name"],
            check_in,
            check_out
        )

        # Клавиатура с двумя вариантами
        buttons = [
            [InlineKeyboardButton(text="🛒 Добавить в заказ", callback_data="hotel:add_to_order")],
            [InlineKeyboardButton(text="✅ Забронировать сейчас", callback_data="hotel:book_now")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            confirmation_text,
            reply_markup=keyboard
        )
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число (от 1)",
            reply_markup=get_back_to_main_keyboard()
        )


# ========== Добавление в заказ и бронирование ==========

@router.callback_query(F.data == "hotel:add_to_order")
async def add_hotel_to_order(callback: CallbackQuery, state: FSMContext):
    """Добавить отель в заказ"""
    await callback.answer("Добавлено в заказ! 🛒")

    data = await state.get_data()
    hotel_id = data.get("selected_hotel_id")
    room_id = data.get("selected_room_id")
    room_count = data.get("room_count", 1)
    check_in = data.get("check_in")
    check_out = data.get("check_out")
    search_island = data.get("search_island")

    hotel = await get_data_loader().get_hotel_by_id(
        int(hotel_id),
        location_code=search_island,
        check_in=check_in,
        check_out=check_out
    )
    room = await get_data_loader().get_room_by_id(int(hotel_id), int(room_id))

    check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
    check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
    nights = (check_out_date - check_in_date).days

    # Добавляем в заказ
    updated_data = order_manager.add_hotel(data, hotel, room, nights * room_count)
    await state.update_data(order=updated_data["order"])

    try:
        await callback.message.delete()
    except:
        pass
    await show_main_menu(callback.message, state)


@router.callback_query(F.data == "hotel:book_now")
async def book_hotel_now(callback: CallbackQuery, state: FSMContext):
    """Забронировать отель сейчас (запросить контакт)"""
    await callback.answer()

    await callback.message.edit_text(
        "Для бронирования поделитесь своими контактными данными.\n\nНаш менеджер свяжется с вами для подтверждения.",
        reply_markup=get_share_contact_keyboard()
    )

    await state.set_state(UserStates.SHARE_CONTACT)


# ========== Кнопки управления ==========

@router.callback_query(F.data == "hotels:back_to_island")
async def back_to_island(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору острова"""
    await callback.answer()

    # Удаляем предыдущее сообщение (может быть с фото)
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем новое сообщение
    await callback.message.answer(
        get_hotels_intro_text(200),
        reply_markup=get_islands_keyboard(),
        parse_mode="Markdown"
    )

    await state.set_state(UserStates.HOTELS_SELECT_ISLAND)


@router.callback_query(F.data == "hotels:back_to_criteria")
async def back_to_criteria(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору критерия"""
    await callback.answer()
    
    await callback.message.edit_text(
        HOTELS_SELECT_CRITERIA,
        reply_markup=get_criteria_keyboard()
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_CRITERIA)


@router.callback_query(F.data == "hotels:change_criteria")
async def change_criteria(callback: CallbackQuery, state: FSMContext):
    """Изменить критерии поиска"""
    await callback.answer()
    await back_to_island(callback, state)


@router.callback_query(F.data.startswith("hotel_from_list:"))
async def show_hotel_from_list(callback: CallbackQuery, state: FSMContext):
    """Показать отель из списка"""
    await callback.answer()
    
    index = int(callback.data.split(":")[1])
    
    # Удаляем сообщение со списком
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем карточку отеля
    await show_hotel_card(callback.message, state, index)
    
    await state.set_state(UserStates.HOTELS_SHOW_RESULTS)


@router.callback_query(F.data == "hotels:back_to_pagination")
async def back_to_pagination(callback: CallbackQuery, state: FSMContext):
    """Вернуться к пагинации отелей"""
    await callback.answer()
    
    data = await state.get_data()
    current_index = data.get("current_hotel_index", 0)
    
    # Удаляем список
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем текущий отель
    await show_hotel_card(callback.message, state, current_index)
    
    await state.set_state(UserStates.HOTELS_SHOW_RESULTS)


@router.callback_query(UserStates.HOTELS_SHOW_RESULTS, F.data.startswith("hotel_view:"))
async def view_hotel_rooms(callback: CallbackQuery, state: FSMContext):
    """Просмотр номеров отеля"""
    await callback.answer()

    hotel_id = callback.data.split(":")[1]
    data = await state.get_data()
    hotels = data.get("hotels", [])

    # Находим отель по ID
    hotel = None
    hotel_index = None
    for i, h in enumerate(hotels):
        if h["id"] == hotel_id:
            hotel = h
            hotel_index = i
            break

    if not hotel:
        await callback.answer("Отель не найден", show_alert=True)
        return

    # Получаем номера отеля (если ещё не загружены - загружаем)
    rooms = hotel.get("rooms", [])
    loading_msg = None
    if not rooms:
        logger.info(f"⚡ Дозагрузка номеров для отеля {hotel['id']}")
        # Показываем сообщение о загрузке
        loading_msg = await show_loading_message(callback.message, "⏳ Загружаю информацию о номерах...")
        try:
            # Получаем location_code и даты из состояния
            search_island = data.get('search_island')
            check_in = data.get('check_in')
            check_out = data.get('check_out')
            # Загружаем номера для этого отеля с актуальными ценами
            hotel_with_rooms = await get_data_loader().get_hotel_by_id(
                int(hotel['id']),
                location_code=search_island,
                check_in=check_in,
                check_out=check_out
            )
            if hotel_with_rooms:
                rooms = hotel_with_rooms.get("rooms", [])
                # Обновляем отель в списке
                hotel['rooms'] = rooms
                hotels[hotel_index] = hotel
                await state.update_data(hotels=hotels)
                logger.info(f"   ✓ Загружено {len(rooms)} номеров")
        except Exception as e:
            logger.error(f"   ❌ Ошибка загрузки номеров: {e}")
            rooms = []
        finally:
            # Удаляем сообщение о загрузке
            if loading_msg:
                await delete_loading_message(loading_msg)

    # Запускаем предзагрузку следующего отеля в фоне
    if hotel_index + 1 < len(hotels):
        next_hotel = hotels[hotel_index + 1]
        if not next_hotel.get("rooms"):
            asyncio.create_task(_preload_hotel_rooms(next_hotel, data))

    if not rooms:
        await callback.answer("Нет доступных номеров", show_alert=True)
        return

    # Формируем текст и клавиатуру
    rooms_text = get_hotel_rooms_text(hotel, rooms)
    keyboard = get_hotel_rooms_keyboard(hotel_id, rooms)

    await callback.message.answer(
        rooms_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(UserStates.HOTELS_SHOW_RESULTS, F.data.startswith("hotel_back:"))
async def back_to_hotel_card(callback: CallbackQuery):
    """Вернуться к карточке отеля из просмотра номеров"""
    await callback.answer()

    # Удаляем сообщение с номерами
    try:
        await callback.message.delete()
    except:
        pass


@router.callback_query(UserStates.HOTELS_SHOW_RESULTS, F.data == "hotels:show_all_list")
async def show_all_hotels_list(callback: CallbackQuery, state: FSMContext):
    """Показать все отели списком"""
    await callback.answer()

    data = await state.get_data()
    hotels = data.get("hotels", [])
    island = data.get("island")
    stars = data.get("stars")
    price_range = data.get("price_range", "Не указана")
    check_in = format_date(data.get("check_in"))
    check_out = format_date(data.get("check_out"))

    if not hotels:
        await callback.answer("Отели не найдены", show_alert=True)
        return

    # Формируем заголовок
    header_text = get_hotels_list_text(
        get_island_name_ru(island),
        f"{stars} звезд" if stars else "Не указана",
        price_range,
        check_in,
        check_out,
        len(hotels)
    )

    # Формируем кнопки с отелями
    buttons = []

    for i, hotel in enumerate(hotels):
        # Получаем все доступные номера отеля
        rooms = hotel.get("rooms", [])

        # Текст кнопки с ценами
        button_text = get_hotel_list_item_text(hotel, rooms)

        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"hotel_from_list:{i}"
        )])

    # Кнопка назад
    buttons.append([InlineKeyboardButton(text="🔙 Вернуться к просмотру", callback_data="hotels:back_to_pagination")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Удаляем предыдущее сообщение (может быть с фото)
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем новое сообщение
    await callback.message.answer(
        header_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(UserStates.HOTELS_SHOW_RESULTS, F.data == "hotels:show_all")
async def show_all_hotels_as_cards(callback: CallbackQuery, state: FSMContext):
    """Показать все отели отдельными блоками (по 10 штук на странице)"""
    await callback.answer()

    data = await state.get_data()
    hotels = data.get("hotels", [])

    if not hotels:
        await callback.answer("Отели не найдены", show_alert=True)
        return

    # Удаляем текущее сообщение с пагинацией
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем первую страницу
    await send_hotels_cards_page(callback.message, state, page=1)


@router.callback_query(UserStates.HOTELS_SHOW_RESULTS, F.data.startswith("cards_page:"))
async def navigate_cards_pages(callback: CallbackQuery, state: FSMContext):
    """Переключение страниц массовых блоков"""
    await callback.answer()

    # Получаем номер страницы
    page = int(callback.data.split(":")[1])

    # Удаляем контрольное сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем новую страницу
    await send_hotels_cards_page(callback.message, state, page)


@router.callback_query(F.data == "current_page")
async def ignore_current_page(callback: CallbackQuery):
    """Игнорируем нажатие на текущую страницу"""
    await callback.answer()


@router.callback_query(F.data == "share:contact")
async def request_contact(callback: CallbackQuery):
    """Запрос контакта пользователя"""
    await callback.answer(
        "📱 Для передачи контакта нажмите на скрепку → Контакт → Отправить мой номер телефона\n\nИли просто напишите номер телефона",
        show_alert=True
    )


@router.message(UserStates.SHARE_CONTACT, F.text)
async def process_phone_number(message: Message, state: FSMContext):
    """Обработка ввода номера телефона"""
    await contact_handler.process_text_phone(message, state)


@router.message(UserStates.SHARE_CONTACT, F.contact)
async def process_contact(message: Message, state: FSMContext):
    """Обработка контакта, отправленного через кнопку"""
    await contact_handler.process_contact(message, state)


@router.callback_query(F.data == "hotels:back_from_calendar")
async def back_from_calendar(callback: CallbackQuery, state: FSMContext):
    """Назад из календаря"""
    await callback.answer()

    data = await state.get_data()
    criteria = data.get("criteria")

    if criteria == "stars":
        await callback.message.edit_text(
            HOTELS_SELECT_STARS,
            reply_markup=get_stars_keyboard()
        )
        await state.set_state(UserStates.HOTELS_SELECT_STARS)
    elif criteria == "price":
        # Для цены возвращаемся к выбору диапазона
        data = await state.get_data()
        currency = data.get("currency", "usd")
        await callback.message.edit_text(
            HOTELS_SELECT_PRICE_RANGE,
            reply_markup=get_price_range_keyboard(currency)
        )
        await state.set_state(UserStates.HOTELS_SELECT_PRICE_RANGE)
    else:
        # Для "all" возвращаемся к выбору критериев
        await callback.message.edit_text(
            HOTELS_SELECT_CRITERIA,
            reply_markup=get_criteria_keyboard()
        )
        await state.set_state(UserStates.HOTELS_SELECT_CRITERIA)


@router.callback_query(F.data == "hotels:back_to_currency")
async def back_to_currency(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору валюты"""
    await callback.answer()
    
    await callback.message.edit_text(
        HOTELS_SELECT_CURRENCY,
        reply_markup=get_currency_keyboard()
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_CURRENCY)


@router.callback_query(F.data == "hotels:back_to_price_method")
async def back_to_price_method(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору метода ввода цены"""
    await callback.answer()
    
    await callback.message.edit_text(
        HOTELS_SELECT_PRICE_METHOD,
        reply_markup=get_price_method_keyboard()
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_PRICE_METHOD)