"""Обработчики флоу экскурсий"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from states.user_states import UserStates
from keyboards import (
    get_islands_keyboard,
    get_excursion_type_keyboard,
    get_group_excursion_keyboard,
    get_no_group_excursions_keyboard,
    get_private_excursion_keyboard,
    get_companions_list_keyboard,
    get_companions_excursion_keyboard,
    get_companions_create_agree_keyboard,
    get_companions_select_excursion_keyboard,
    get_share_contact_keyboard,
    get_back_to_main_keyboard
)
from utils.texts import (
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
    get_companions_created_text,
    CONTACT_RECEIVED
)
from utils.helpers import (
    get_calendar_keyboard,
    get_island_name_ru,
    format_date,
    validate_phone_number,
    send_items_page
)
from utils.data_loader import get_data_loader
from utils.media_manager import get_excursion_photo
from utils.contact_handler import contact_handler
from utils.order_manager import order_manager

router = Router()

EXCURSIONS_PER_PAGE = 5
MAX_EXCURSION_NAME_LENGTH = 40


# ========== Старт флоу экскурсий ==========

@router.callback_query(F.data == "main:excursions")
async def start_excursions_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу экскурсий - выбор острова"""
    await callback.answer()
    
    data = await state.get_data()
    user_name = data.get("user_name", "Друг")
    
    await callback.message.edit_text(
        get_excursions_intro_text(user_name),
        reply_markup=get_islands_keyboard()
    )
    
    await state.set_state(UserStates.EXCURSIONS_SELECT_ISLAND)


# ========== Выбор острова ==========

@router.callback_query(UserStates.EXCURSIONS_SELECT_ISLAND, F.data.startswith("island:"))
async def select_island_for_excursions(callback: CallbackQuery, state: FSMContext):
    """Выбор острова для экскурсий"""
    await callback.answer()
    
    island_code = callback.data.split(":")[1]
    
    if island_code == "other":
        await callback.answer("Функция в разработке", show_alert=True)
        return
    
    await state.update_data(island=island_code)
    
    await callback.message.edit_text(
        EXCURSIONS_SELECT_TYPE,
        reply_markup=get_excursion_type_keyboard()
    )
    
    await state.set_state(UserStates.EXCURSIONS_SELECT_TYPE)


# ========== ВЕТКА A: Групповые экскурсии ==========

@router.callback_query(UserStates.EXCURSIONS_SELECT_TYPE, F.data == "exc_type:group")
async def select_group_excursions(callback: CallbackQuery, state: FSMContext):
    """Выбор групповых экскурсий"""
    await callback.answer()
    
    await callback.message.edit_text(EXCURSIONS_GROUP_INTRO)

    # Показываем календарь
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month, back_callback="excursions:back_from_calendar")

    await callback.message.answer(
        "Выберите дату:",
        reply_markup=calendar
    )

    await state.set_state(UserStates.EXCURSIONS_GROUP_SELECT_DATE)


@router.callback_query(UserStates.EXCURSIONS_GROUP_SELECT_DATE, F.data.startswith("cal:"))
async def navigate_group_calendar(callback: CallbackQuery):
    """Навигация по календарю групповых экскурсий"""
    await callback.answer()

    date_str = callback.data.split(":")[1]

    if date_str == "ignore":
        return

    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month, back_callback="excursions:back_from_calendar")

    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.EXCURSIONS_GROUP_SELECT_DATE, F.data.startswith("date:"))
async def select_group_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для групповых экскурсий"""
    await callback.answer()
    
    date = callback.data.split(":")[1]
    data = await state.get_data()
    island = data.get("island")
    
    # Получаем экскурсии на эту дату
    excursions = get_data_loader().get_excursions_by_filters(
        island=island,
        excursion_type="group",
        date=date
    )
    
    if not excursions:
        await callback.message.edit_text(
            NO_EXCURSIONS_FOUND,
            reply_markup=get_no_group_excursions_keyboard()
        )
        return
    
    # Сохраняем данные
    await state.update_data(
        excursions=excursions,
        current_date=date,
        current_excursion_index=0
    )
    
    # Удаляем сообщение с календарем
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем первую экскурсию
    await show_group_excursion(callback.message, state, 0)


async def show_group_excursion(message: Message, state: FSMContext, index: int, expanded: bool = False):
    """Показать карточку групповой экскурсии"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    
    if not excursions or index >= len(excursions):
        return
    
    excursion = excursions[index]
    card_text = get_group_excursion_card_text(excursion, expanded)
    
    # Проверяем наличие других экскурсий на эту же дату (для пагинации)
    has_prev = index > 0
    has_next = index < len(excursions) - 1
    
    # Создаем клавиатуру с пагинацией между экскурсиями
    buttons = []
    
    # Кнопка присоединиться
    buttons.append([InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"exc_join:{excursion['id']}")])
    
    # Кнопка развернуть/свернуть
    if expanded:
        buttons.append([InlineKeyboardButton(text="Свернуть ▲", callback_data=f"exc_group_collapse:{index}")])
    else:
        buttons.append([InlineKeyboardButton(text="Развернуть ▼", callback_data=f"exc_group_expand:{index}")])
    
    # Пагинация между экскурсиями на одну дату
    if has_prev or has_next:
        nav_buttons = []
        if has_prev:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"exc_group_nav:prev:{index}"))
        if has_next:
            nav_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"exc_group_nav:next:{index}"))
        buttons.append(nav_buttons)

    # Кнопка показать все страницей
    buttons.append([InlineKeyboardButton(text="📋 Показать все страницей", callback_data="exc_group:show_all")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Пытаемся получить фото
    photo = await get_excursion_photo(excursion["id"])
    
    if photo:
        await message.answer_photo(
            photo=photo,
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


async def _update_group_excursion_card(callback: CallbackQuery, state: FSMContext, index: int, expanded: bool):
    """Вспомогательная функция для обновления карточки групповой экскурсии"""
    data = await state.get_data()
    excursions = data.get("excursions", [])

    if not excursions or index >= len(excursions):
        return

    excursion = excursions[index]
    card_text = get_group_excursion_card_text(excursion, expanded=expanded)

    has_prev = index > 0
    has_next = index < len(excursions) - 1

    buttons = []
    buttons.append([InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"exc_join:{excursion['id']}")])

    if expanded:
        buttons.append([InlineKeyboardButton(text="Свернуть ▲", callback_data=f"exc_group_collapse:{index}")])
    else:
        buttons.append([InlineKeyboardButton(text="Развернуть ▼", callback_data=f"exc_group_expand:{index}")])

    if has_prev or has_next:
        nav_buttons = []
        if has_prev:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"exc_group_nav:prev:{index}"))
        if has_next:
            nav_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"exc_group_nav:next:{index}"))
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="📋 Показать все страницей", callback_data="exc_group:show_all")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Получаем фото и отправляем новое сообщение
    photo = await get_excursion_photo(excursion["id"])

    if photo:
        await callback.message.answer_photo(
            photo=photo,
            caption=card_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            card_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


@router.callback_query(F.data.startswith("exc_group_expand:"))
async def expand_group_excursion(callback: CallbackQuery, state: FSMContext):
    """Развернуть описание групповой экскурсии"""
    await callback.answer()
    index = int(callback.data.split(":")[1])
    await _update_group_excursion_card(callback, state, index, expanded=True)


@router.callback_query(F.data.startswith("exc_group_collapse:"))
async def collapse_group_excursion(callback: CallbackQuery, state: FSMContext):
    """Свернуть описание групповой экскурсии"""
    await callback.answer()
    index = int(callback.data.split(":")[1])
    await _update_group_excursion_card(callback, state, index, expanded=False)


@router.callback_query(F.data.startswith("exc_group_nav:"))
async def navigate_group_excursions(callback: CallbackQuery, state: FSMContext):
    """Навигация между групповыми экскурсиями на одну дату"""
    await callback.answer()
    
    parts = callback.data.split(":")
    direction = parts[1]
    current_index = int(parts[2])
    
    new_index = current_index - 1 if direction == "prev" else current_index + 1
    
    await state.update_data(current_excursion_index=new_index)

    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем новую экскурсию
    await show_group_excursion(callback.message, state, new_index)


async def send_excursions_cards_page(message: Message, state: FSMContext, page: int):
    """Отправить страницу с экскурсиями (по 5 штук)"""
    data = await state.get_data()
    excursions = data.get("excursions", [])

    if not excursions:
        return

    # Функция форматирования карточки
    def format_card(excursion):
        return get_group_excursion_card_text(excursion, expanded=False)

    # Функция создания клавиатуры
    def get_keyboard(excursion):
        buttons = [
            [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"exc_join:{excursion['id']}")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Функция получения фото
    async def get_photo(excursion):
        return await get_excursion_photo(excursion["id"])

    # Используем универсальную функцию
    await send_items_page(
        message=message,
        items=excursions,
        page=page,
        per_page=EXCURSIONS_PER_PAGE,
        format_card_func=format_card,
        get_keyboard_func=get_keyboard,
        get_photo_func=get_photo,
        callback_prefix="exc_cards_page",
        page_title="Страница",
        parse_mode="Markdown",
        page_1_based=True
    )


@router.callback_query(F.data == "exc_group:show_all")
async def show_all_group_excursions(callback: CallbackQuery, state: FSMContext):
    """Показать все групповые экскурсии страницей"""
    await callback.answer()

    data = await state.get_data()
    excursions = data.get("excursions", [])

    if not excursions:
        await callback.answer("Экскурсии не найдены", show_alert=True)
        return

    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем первую страницу
    await send_excursions_cards_page(callback.message, state, page=1)


@router.callback_query(F.data.startswith("exc_cards_page:"))
async def navigate_excursions_pages(callback: CallbackQuery, state: FSMContext):
    """Переключение страниц экскурсий"""
    await callback.answer()

    # Получаем номер страницы
    page = int(callback.data.split(":")[1])

    # Удаляем контрольное сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем новую страницу
    await send_excursions_cards_page(callback.message, state, page)


@router.callback_query(F.data.startswith("exc_join:"))
async def join_group_excursion(callback: CallbackQuery, state: FSMContext):
    """Присоединиться к групповой экскурсии"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]
    excursion = get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    await state.update_data(selected_excursion_id=excursion_id, excursion_people_count=1)

    # Клавиатура с двумя вариантами
    buttons = [
        [InlineKeyboardButton(text="🛒 Добавить в заказ", callback_data="exc_group:add_to_order")],
        [InlineKeyboardButton(text="✅ Забронировать сейчас", callback_data="exc_group:book_now")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(
        get_excursion_join_text(excursion["name"]),
        reply_markup=keyboard
    )


# ========== ВЕТКА B: Индивидуальные экскурсии ==========

@router.callback_query(UserStates.EXCURSIONS_SELECT_TYPE, F.data == "exc_type:private")
async def select_private_excursions(callback: CallbackQuery, state: FSMContext):
    """Выбор индивидуальных экскурсий"""
    await callback.answer()
    
    await callback.message.edit_text(
        EXCURSIONS_PRIVATE_INTRO,
        reply_markup=get_back_to_main_keyboard()
    )
    
    await state.set_state(UserStates.EXCURSIONS_PRIVATE_INPUT_PEOPLE)


@router.message(UserStates.EXCURSIONS_PRIVATE_INPUT_PEOPLE, F.text)
async def process_private_people_count(message: Message, state: FSMContext):
    """Обработка количества человек для индивидуальных экскурсий"""
    try:
        people_count = int(message.text.strip())
        
        if people_count < 1:
            raise ValueError
        
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        data = await state.get_data()
        island = data.get("island")
        
        # Получаем индивидуальные экскурсии
        excursions = get_data_loader().get_excursions_by_filters(
            island=island,
            excursion_type="private"
        )
        
        if not excursions:
            await message.answer(
                "😔 К сожалению, индивидуальных экскурсий не найдено.",
                reply_markup=get_back_to_main_keyboard()
            )
            return
        
        await state.update_data(
            people_count=people_count,
            excursions=excursions,
            current_excursion_index=0
        )
        
        # Показываем первую экскурсию
        await show_private_excursion(message, state, 0)
        
        await state.set_state(UserStates.EXCURSIONS_SHOW_RESULTS)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число",
            reply_markup=get_back_to_main_keyboard()
        )


async def show_private_excursion(message: Message, state: FSMContext, index: int, expanded: bool = False):
    """Показать карточку индивидуальной экскурсии"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("people_count", 1)
    
    if not excursions or index >= len(excursions):
        return
    
    excursion = excursions[index]
    card_text = get_private_excursion_card_text(excursion, people_count, expanded)
    
    keyboard = get_private_excursion_keyboard(
        excursion["id"],
        index,
        len(excursions),
        expanded,
        excursion.get("url")
    )
    
    # Пытаемся получить фото
    photo = await get_excursion_photo(excursion["id"])
    
    if photo:
        await message.answer_photo(
            photo=photo,
            caption=card_text,
            reply_markup=keyboard
        )
    else:
        await message.answer(
            card_text,
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("exc_private_expand:"))
async def expand_private_excursion(callback: CallbackQuery, state: FSMContext):
    """Развернуть описание индивидуальной экскурсии"""
    await callback.answer()

    index = int(callback.data.split(":")[2])
    
    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем развернутую версию
    await show_private_excursion(callback.message, state, index, expanded=True)


@router.callback_query(F.data.startswith("exc_private_collapse:"))
async def collapse_private_excursion(callback: CallbackQuery, state: FSMContext):
    """Свернуть описание индивидуальной экскурсии"""
    await callback.answer()

    index = int(callback.data.split(":")[2])
    
    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем свернутую версию
    await show_private_excursion(callback.message, state, index, expanded=False)


@router.callback_query(UserStates.EXCURSIONS_SHOW_RESULTS, F.data.startswith("exc_nav:"))
async def navigate_private_excursions(callback: CallbackQuery, state: FSMContext):
    """Навигация по индивидуальным экскурсиям"""
    await callback.answer()
    
    parts = callback.data.split(":")
    direction = parts[1]
    current_index = int(parts[2])
    
    new_index = current_index - 1 if direction == "prev" else current_index + 1
    
    await state.update_data(current_excursion_index=new_index)
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await show_private_excursion(callback.message, state, new_index)


@router.callback_query(UserStates.EXCURSIONS_SHOW_RESULTS, F.data.startswith("exc_book:"))
async def book_private_excursion(callback: CallbackQuery, state: FSMContext):
    """Бронирование индивидуальной экскурсии"""
    await callback.answer()
    
    excursion_id = callback.data.split(":")[1]
    await state.update_data(selected_excursion_id=excursion_id)

    # Показываем календарь выбора даты
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month, back_callback="excursions:back_private_from_calendar")

    await callback.message.answer(
        "Выберите дату:",
        reply_markup=calendar
    )

    await state.set_state(UserStates.EXCURSIONS_PRIVATE_SELECT_DATE)


@router.callback_query(UserStates.EXCURSIONS_PRIVATE_SELECT_DATE, F.data.startswith("cal:"))
async def navigate_private_calendar(callback: CallbackQuery):
    """Навигация по календарю для индивидуальных экскурсий"""
    await callback.answer()

    date_str = callback.data.split(":")[1]

    if date_str == "ignore":
        return

    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month, back_callback="excursions:back_private_from_calendar")

    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.EXCURSIONS_PRIVATE_SELECT_DATE, F.data.startswith("date:"))
async def select_private_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для индивидуальной экскурсии"""
    await callback.answer()

    date = callback.data.split(":")[1]

    data = await state.get_data()
    excursion_id = data.get("selected_excursion_id")
    people_count = data.get("people_count")

    excursion = get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    await state.update_data(excursion_people_count=people_count)

    # Клавиатура с двумя вариантами
    buttons = [
        [InlineKeyboardButton(text="🛒 Добавить в заказ", callback_data="exc_private:add_to_order")],
        [InlineKeyboardButton(text="✅ Забронировать сейчас", callback_data="exc_private:book_now")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        get_excursion_booking_text(excursion["name"], people_count, format_date(date)),
        reply_markup=keyboard
    )


# ========== ВЕТКА C: Поиск попутчиков ==========

@router.callback_query(UserStates.EXCURSIONS_SELECT_TYPE, F.data == "exc_type:companions")
async def select_companions(callback: CallbackQuery, state: FSMContext):
    """Поиск попутчиков"""
    await callback.answer()
    
    await callback.message.edit_text(COMPANIONS_INTRO)
    
    # Показываем список за текущий месяц
    now = datetime.now()
    await show_companions_list(callback.message, state, now.year, now.month)
    
    await state.set_state(UserStates.COMPANIONS_VIEW_LIST)


async def show_companions_list(message: Message, state: FSMContext, year: int, month: int):
    """Показать список экскурсий с поиском попутчиков"""
    data = await state.get_data()
    island = data.get("island")
    
    # Получаем экскурсии за месяц
    excursions = get_data_loader().get_companions_by_month(island, year, month)
    
    await state.update_data(
        companions_month=month, 
        companions_year=year,
        companions_excursions=excursions
    )
    
    # Формируем текст заголовка
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    text = f"**Экскурсии с поиском попутчиков**\n{month_names[month-1]} {year}\n\n"
    
    if not excursions:
        text += "На выбранный месяц экскурсий пока нет."
        keyboard = get_companions_list_keyboard(month, year)
        
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        # Формируем кнопки для каждой экскурсии
        buttons = []
        
        for exc in excursions:
            # Текст кнопки: дата + название (обрезаем если длинное)
            button_text = f"📅 {format_date(exc['date'])} - {exc['name'][:MAX_EXCURSION_NAME_LENGTH]}"
            if len(exc['name']) > MAX_EXCURSION_NAME_LENGTH:
                button_text += "..."
            
            buttons.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"comp_view:{exc['id']}"
            )])
        
        # Навигация по месяцам
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        buttons.append([
            InlineKeyboardButton(text="⬅️", callback_data=f"comp_month:{prev_year}-{prev_month:02d}"),
            InlineKeyboardButton(text=f"{month_names[month-1]} {year}", callback_data="comp_month:ignore"),
            InlineKeyboardButton(text="➡️", callback_data=f"comp_month:{next_year}-{next_month:02d}")
        ])
        
        buttons.append([InlineKeyboardButton(text="➕ Создать свою заявку", callback_data="comp_create:start")])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_type")])
        buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("comp_view:"))
async def view_companion_excursion(callback: CallbackQuery, state: FSMContext):
    """Просмотр детальной информации об экскурсии с попутчиками"""
    await callback.answer()
    
    excursion_id = callback.data.split(":")[1]
    excursion = get_data_loader().get_excursion_by_id(excursion_id)
    
    if not excursion:
        return
    
    # Показываем детальную карточку
    card_text = get_companions_excursion_card_text(excursion)
    keyboard = get_companions_excursion_keyboard(excursion_id, excursion.get("url"))
    
    await callback.message.answer(
        card_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("comp_join:"))
async def join_companion_excursion(callback: CallbackQuery, state: FSMContext):
    """Присоединиться к экскурсии с попутчиками"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]
    excursion = get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    await state.update_data(selected_excursion_id=excursion_id, excursion_people_count=1)

    # Клавиатура с двумя вариантами
    buttons = [
        [InlineKeyboardButton(text="🛒 Добавить в заказ", callback_data="exc_companion:add_to_order")],
        [InlineKeyboardButton(text="✅ Забронировать сейчас", callback_data="exc_companion:book_now")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(
        get_excursion_join_text(excursion["name"]),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "comp_back:list")
async def back_to_companions_list(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку попутчиков"""
    await callback.answer()
    
    data = await state.get_data()
    year = data.get("companions_year", datetime.now().year)
    month = data.get("companions_month", datetime.now().month)
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await show_companions_list(callback.message, state, year, month)
    
    await state.set_state(UserStates.COMPANIONS_VIEW_LIST)


@router.callback_query(F.data.startswith("comp_month:"))
async def navigate_companions_month(callback: CallbackQuery, state: FSMContext):
    """Навигация по месяцам для попутчиков"""
    await callback.answer()
    
    month_str = callback.data.split(":")[1]
    
    if month_str == "ignore":
        return
    
    year, month = map(int, month_str.split("-"))
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await show_companions_list(callback.message, state, year, month)


@router.callback_query(F.data == "comp_create:start")
async def create_companion_request_start(callback: CallbackQuery):
    """Начало создания заявки на поиск попутчиков"""
    await callback.answer()
    
    await callback.message.answer(
        COMPANIONS_HOW_IT_WORKS,
        reply_markup=get_companions_create_agree_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "comp_create:agree")
async def create_companion_agree(callback: CallbackQuery, state: FSMContext):
    """Согласие с условиями поиска попутчиков"""
    await callback.answer()
    
    data = await state.get_data()
    island = data.get("island")
    
    # Получаем все экскурсии для выбора
    excursions = get_data_loader().get_excursions_by_filters(island=island)
    
    if not excursions:
        await callback.message.edit_text(
            "😔 К сожалению, экскурсий не найдено.",
            reply_markup=get_back_to_main_keyboard()
        )
        return
    
    await state.update_data(available_excursions=excursions)

    await callback.message.edit_text(
        COMPANIONS_SELECT_EXCURSION,
        reply_markup=get_companions_select_excursion_keyboard(excursions)
    )
    
    await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION, F.data.startswith("comp_select_exc:"))
async def select_excursion_for_companion(callback: CallbackQuery, state: FSMContext):
    """Выбор экскурсии для создания заявки - сразу запрашиваем контакт"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]
    excursion = get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    await state.update_data(selected_excursion_id=excursion_id)

    # Сразу запрашиваем контакт для создания заявки попутчика
    await callback.message.edit_text(
        get_excursion_join_text(excursion["name"]),
        reply_markup=get_share_contact_keyboard()
    )

    await state.set_state(UserStates.SHARE_CONTACT)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_DATE, F.data.startswith("cal:"))
async def navigate_companion_calendar(callback: CallbackQuery):
    """Навигация по календарю для создания заявки"""
    await callback.answer()

    date_str = callback.data.split(":")[1]

    if date_str == "ignore":
        return

    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month, back_callback="excursions:back_companion_from_calendar")

    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_DATE, F.data.startswith("date:"))
async def select_date_for_companion(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для заявки"""
    await callback.answer()
    
    date = callback.data.split(":")[1]
    await state.update_data(companion_date=date)
    
    await callback.message.edit_text(
        COMPANIONS_INPUT_PEOPLE,
        reply_markup=get_back_to_main_keyboard()
    )
    
    await state.set_state(UserStates.COMPANIONS_CREATE_INPUT_PEOPLE)


@router.message(UserStates.COMPANIONS_CREATE_INPUT_PEOPLE, F.text)
async def process_companion_people_count(message: Message, state: FSMContext):
    """Обработка количества человек для заявки"""
    try:
        people_count = int(message.text.strip())
        
        if people_count < 1:
            raise ValueError
        
        # Удаляем сообщение
        try:
            await message.delete()
        except:
            pass
        
        data = await state.get_data()
        excursion_id = data.get("selected_excursion_id")
        date = data.get("companion_date")
        
        excursion = get_data_loader().get_excursion_by_id(excursion_id)
        
        if not excursion:
            return
        
        await state.update_data(people_count=people_count, excursion_people_count=people_count)

        # Клавиатура с двумя вариантами
        buttons = [
            [InlineKeyboardButton(text="🛒 Добавить в заказ", callback_data="exc_create:add_to_order")],
            [InlineKeyboardButton(text="✅ Забронировать сейчас", callback_data="exc_create:book_now")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        # Показываем подтверждение
        await message.answer(
            get_companions_created_text(excursion["name"], format_date(date), people_count),
            reply_markup=keyboard
        )
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число",
            reply_markup=get_back_to_main_keyboard()
        )


# ========== Добавление в заказ и бронирование ==========

@router.callback_query(F.data == "exc_group:add_to_order")
@router.callback_query(F.data == "exc_companion:add_to_order")
@router.callback_query(F.data == "exc_private:add_to_order")
@router.callback_query(F.data == "exc_create:add_to_order")
async def add_excursion_to_order(callback: CallbackQuery, state: FSMContext):
    """Добавить экскурсию в заказ"""
    await callback.answer("Добавлено в заказ! 🛒")

    data = await state.get_data()
    excursion_id = data.get("selected_excursion_id")
    people_count = data.get("excursion_people_count", 1)

    excursion = get_data_loader().get_excursion_by_id(excursion_id)

    # Добавляем в заказ
    updated_data = order_manager.add_excursion(data, excursion, people_count)
    await state.update_data(order=updated_data["order"])

    # Возвращаем в главное меню
    from handlers.main_menu import show_main_menu
    try:
        await callback.message.delete()
    except:
        pass
    await show_main_menu(callback.message, state)


@router.callback_query(F.data == "exc_group:book_now")
@router.callback_query(F.data == "exc_companion:book_now")
@router.callback_query(F.data == "exc_private:book_now")
@router.callback_query(F.data == "exc_create:book_now")
async def book_excursion_now(callback: CallbackQuery, state: FSMContext):
    """Забронировать экскурсию сейчас (запросить контакт)"""
    await callback.answer()

    await callback.message.edit_text(
        "Для бронирования поделитесь своими контактными данными.\n\nНаш менеджер свяжется с вами для подтверждения.",
        reply_markup=get_share_contact_keyboard()
    )

    await state.set_state(UserStates.SHARE_CONTACT)


# ========== Обработка контактов для экскурсий ==========

@router.message(UserStates.SHARE_CONTACT, F.text)
async def process_excursion_phone(message: Message, state: FSMContext):
    """Обработка номера телефона для экскурсий"""
    await contact_handler.process_text_phone(message, state)


@router.message(UserStates.SHARE_CONTACT, F.contact)
async def process_excursion_contact(message: Message, state: FSMContext):
    """Обработка контакта для экскурсий"""
    await contact_handler.process_contact(message, state)


# ========== Навигация назад ==========

@router.callback_query(F.data == "excursions:back_to_island")
async def back_to_island_excursions(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору острова"""
    await callback.answer()
    
    data = await state.get_data()
    user_name = data.get("user_name", "Друг")
    
    await callback.message.edit_text(
        get_excursions_intro_text(user_name),
        reply_markup=get_islands_keyboard()
    )
    
    await state.set_state(UserStates.EXCURSIONS_SELECT_ISLAND)


@router.callback_query(F.data == "excursions:back_to_type")
async def back_to_type_excursions(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору типа экскурсии"""
    await callback.answer()
    
    await callback.message.edit_text(
        EXCURSIONS_SELECT_TYPE,
        reply_markup=get_excursion_type_keyboard()
    )
    
    await state.set_state(UserStates.EXCURSIONS_SELECT_TYPE)


@router.callback_query(F.data.startswith("exc_view:"))
async def view_excursion_details(callback: CallbackQuery):
    """Просмотр деталей экскурсии (заглушка для экскурсий без URL)"""
    await callback.answer("Ссылка на эту экскурсию пока недоступна", show_alert=True)


@router.callback_query(F.data == "excursions:back_from_calendar")
async def back_from_group_calendar(callback: CallbackQuery, state: FSMContext):
    """Назад из календаря групповых экскурсий"""
    await callback.answer()

    # Удаляем календарь
    try:
        await callback.message.delete()
    except:
        pass

    # Возвращаемся к выбору типа экскурсии
    await callback.message.answer(
        EXCURSIONS_SELECT_TYPE,
        reply_markup=get_excursion_type_keyboard()
    )

    await state.set_state(UserStates.EXCURSIONS_SELECT_TYPE)


@router.callback_query(F.data == "excursions:back_private_from_calendar")
async def back_from_private_calendar(callback: CallbackQuery, state: FSMContext):
    """Назад из календаря индивидуальных экскурсий"""
    await callback.answer()

    # Удаляем календарь
    try:
        await callback.message.delete()
    except:
        pass

    # Возвращаемся к списку индивидуальных экскурсий
    data = await state.get_data()
    current_index = data.get("current_excursion_index", 0)

    await show_private_excursion(callback.message, state, current_index)

    await state.set_state(UserStates.EXCURSIONS_SHOW_RESULTS)


@router.callback_query(F.data == "excursions:back_companion_from_calendar")
async def back_from_companion_calendar(callback: CallbackQuery, state: FSMContext):
    """Назад из календаря создания заявки попутчиков"""
    await callback.answer()

    # Удаляем календарь
    try:
        await callback.message.delete()
    except:
        pass

    # Возвращаемся к выбору экскурсии
    data = await state.get_data()
    island = data.get("island")

    excursions = get_data_loader().get_excursions_by_filters(island=island)

    await callback.message.answer(
        COMPANIONS_SELECT_EXCURSION,
        reply_markup=get_companions_select_excursion_keyboard(excursions)
    )

    await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)