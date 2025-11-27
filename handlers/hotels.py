"""Обработчики флоу отелей"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

from states.user_states import UserStates
from keyboards import (
    get_islands_keyboard,
    get_criteria_keyboard,
    get_stars_keyboard,
    get_currency_keyboard,
    get_price_method_keyboard,
    get_price_range_keyboard,
    get_hotel_navigation_keyboard,
    get_share_contact_keyboard,
    get_back_to_main_keyboard
)
from utils.texts import (
    get_hotels_intro_text,
    HOTELS_SELECT_CRITERIA,
    HOTELS_SELECT_STARS,
    HOTELS_SELECT_CURRENCY,
    HOTELS_SELECT_PRICE_METHOD,
    HOTELS_INPUT_CUSTOM_RANGE,
    HOTELS_SELECT_PRICE_RANGE,
    HOTELS_SELECT_CHECK_IN,
    HOTELS_SELECT_CHECK_OUT,
    get_hotels_confirmation_text,
    get_hotel_card_text,
    HOTELS_INPUT_ROOM_COUNT,
    get_booking_confirmation_text,
    CONTACT_RECEIVED,
    get_hotels_list_text,
    get_hotel_list_item_text
)
from utils.helpers import (
    validate_price_range,
    get_calendar_keyboard,
    get_island_name_ru,
    format_date,
    get_currency_symbol,
    convert_price,
    validate_phone_number
)
from utils.data_loader import data_loader
from utils.media_manager import get_hotel_photo
from utils.contact_handler import contact_handler
from utils.order_manager import order_manager

router = Router()


# ========== Старт флоу отелей ==========

@router.callback_query(F.data == "main:hotels")
async def start_hotels_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу отелей - вступительное сообщение"""
    await callback.answer()
    
    hotels_count = data_loader.get_hotels_count()
    
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
        # TODO: Реализовать ввод текстом
        await callback.answer("Функция в разработке", show_alert=True)
        return
    
    # Сохраняем остров
    await state.update_data(island=island_code)
    
    await callback.message.edit_text(
        HOTELS_SELECT_CRITERIA,
        reply_markup=get_criteria_keyboard()
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_CRITERIA)


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
    
    await callback.message.edit_text(
        HOTELS_INPUT_CUSTOM_RANGE,
        reply_markup=get_back_to_main_keyboard()
    )
    
    await state.set_state(UserStates.HOTELS_INPUT_CUSTOM_RANGE)


@router.callback_query(UserStates.HOTELS_SELECT_PRICE_METHOD, F.data == "price_method:list")
async def select_price_method_list(callback: CallbackQuery, state: FSMContext):
    """Выбран метод - диапазон из списка"""
    await callback.answer()
    
    await callback.message.edit_text(
        HOTELS_SELECT_PRICE_RANGE,
        reply_markup=get_price_range_keyboard()
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_PRICE_RANGE)


@router.message(UserStates.HOTELS_INPUT_CUSTOM_RANGE, F.text)
async def process_custom_price_range(message: Message, state: FSMContext):
    """Обработка ввода собственного диапазона"""
    valid, min_price, max_price = validate_price_range(message.text)
    
    if not valid:
        await message.answer(
            "❌ Неверный формат! Пожалуйста, введите диапазон в формате: 50-1000",
            reply_markup=get_back_to_main_keyboard()
        )
        return
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    await state.update_data(
        price_range=f"{min_price}-{max_price}",
        min_price=min_price,
        max_price=max_price
    )
    
    # Переходим к выбору дат
    await show_check_in_calendar_new_message(message, state)


@router.callback_query(UserStates.HOTELS_SELECT_PRICE_RANGE, F.data.startswith("price_range:"))
async def select_price_range(callback: CallbackQuery, state: FSMContext):
    """Выбор диапазона из списка"""
    await callback.answer()
    
    price_range = callback.data.split(":")[1]
    min_price, max_price = map(int, price_range.split("-"))
    
    await state.update_data(
        price_range=price_range,
        min_price=min_price,
        max_price=max_price
    )
    
    # Переходим к выбору дат
    await show_check_in_calendar(callback.message, state)


# ========== Календарь и даты ==========

async def show_check_in_calendar(message: Message, state: FSMContext):
    """Показать календарь выбора даты заезда"""
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month)
    
    await message.edit_text(
        HOTELS_SELECT_CHECK_IN,
        reply_markup=calendar
    )
    
    await state.set_state(UserStates.HOTELS_SELECT_CHECK_IN)


async def show_check_in_calendar_new_message(message: Message, state: FSMContext):
    """Показать календарь в новом сообщении"""
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month)
    
    await message.answer(
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
    await state.update_data(check_out=check_out)
    
    # Показываем подтверждение и результаты
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
    
    # Получаем отели по фильтрам
    hotels = data_loader.get_hotels_by_filters(
        island=island,
        stars=stars,
        min_price=min_price,
        max_price=max_price
    )
    
    if not hotels:
        await message.edit_text(
            f"😔 К сожалению, по вашим критериям отели не найдены.\n\nПопробуйте изменить параметры поиска.",
            reply_markup=get_back_to_main_keyboard()
        )
        return
    
    # Сохраняем отели и индекс
    await state.update_data(hotels=hotels, current_hotel_index=0)
    
    # Показываем подтверждение
    confirmation_text = get_hotels_confirmation_text(
        user_name,
        get_island_name_ru(island),
        f"{stars} звезд" if stars else "Не указана",
        price_range,
        check_in,
        check_out
    )
    
    await message.edit_text(confirmation_text)
    
    # Показываем первый отель
    await show_hotel_card(message, state, 0)
    
    await state.set_state(UserStates.HOTELS_SHOW_RESULTS)


async def show_hotel_card(message: Message, state: FSMContext, index: int):
    """Показать карточку отеля"""
    data = await state.get_data()
    hotels = data.get("hotels", [])
    min_price = data.get("min_price")
    max_price = data.get("max_price")
    
    if index < 0 or index >= len(hotels):
        return
    
    hotel = hotels[index]
    
    # Фильтруем комнаты по цене
    rooms = hotel.get("rooms", [])
    if min_price and max_price:
        rooms = data_loader.filter_rooms_by_price(rooms, min_price, max_price)
    
    # Формируем текст карточки
    card_text = get_hotel_card_text(hotel, rooms)
    
    # Формируем клавиатуру
    keyboard = get_hotel_navigation_keyboard(
        current_index=index,
        total=len(hotels),
        hotel_id=hotel["id"],
        rooms=rooms
    )
    
    # Пытаемся получить фото
    photo = await get_hotel_photo(hotel["id"])
    
    if photo:
        # Отправляем с фото
        await message.answer_photo(
            photo=photo,
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
        
        if room_count < 1 or room_count > 9:
            raise ValueError
        
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        data = await state.get_data()
        hotel_id = data.get("selected_hotel_id")
        room_id = data.get("selected_room_id")
        check_in = format_date(data.get("check_in"))
        check_out = format_date(data.get("check_out"))
        
        hotel = data_loader.get_hotel_by_id(hotel_id)
        room = data_loader.get_room_by_id(hotel_id, room_id)

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
            "❌ Пожалуйста, введите число от 1 до 9",
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

    hotel = data_loader.get_hotel_by_id(hotel_id)
    room = data_loader.get_room_by_id(hotel_id, room_id)

    # Рассчитываем количество ночей
    from datetime import datetime
    check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
    check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
    nights = (check_out_date - check_in_date).days

    # Добавляем в заказ
    updated_data = order_manager.add_hotel(data, hotel, room, nights * room_count)
    await state.update_data(order=updated_data["order"])

    # Возвращаем в главное меню
    from handlers.main_menu import show_main_menu
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

    hotels_count = data_loader.get_hotels_count()

    # Удаляем предыдущее сообщение (может быть с фото)
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем новое сообщение
    await callback.message.answer(
        get_hotels_intro_text(hotels_count),
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


@router.callback_query(F.data == "hotels:show_all")
async def show_all_hotels_list(callback: CallbackQuery, state: FSMContext):
    """Показать все отели списком"""
    await callback.answer()
    
    data = await state.get_data()
    hotels = data.get("hotels", [])
    user_name = data.get("user_name", "Друг")
    island = data.get("island")
    stars = data.get("stars")
    price_range = data.get("price_range", "Не указана")
    check_in = format_date(data.get("check_in"))
    check_out = format_date(data.get("check_out"))
    min_price = data.get("min_price")
    max_price = data.get("max_price")
    
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
        # Фильтруем комнаты по цене
        rooms = hotel.get("rooms", [])
        if min_price and max_price:
            rooms = data_loader.filter_rooms_by_price(rooms, min_price, max_price)
        
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


@router.callback_query(F.data.startswith("hotel_view:"))
async def view_hotel_details(callback: CallbackQuery):
    """Просмотр деталей отеля"""
    await callback.answer("🔍 Функция просмотра отеля будет реализована позже", show_alert=True)


@router.callback_query(F.data == "hotels:show_all")
async def show_all_hotels_list(callback: CallbackQuery):
    """Показать все отели списком"""
    await callback.answer("📋 Функция показа списком будет реализована позже", show_alert=True)


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
    else:
        # Для цены возвращаемся к выбору диапазона
        await callback.message.edit_text(
            HOTELS_SELECT_PRICE_RANGE,
            reply_markup=get_price_range_keyboard()
        )
        await state.set_state(UserStates.HOTELS_SELECT_PRICE_RANGE)


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