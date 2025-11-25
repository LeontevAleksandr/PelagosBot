"""Обработчики флоу экскурсий"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
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
    validate_phone_number
)
from utils.data_loader import data_loader

router = Router()


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
    calendar = get_calendar_keyboard(now.year, now.month)
    
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
    calendar = get_calendar_keyboard(year, month)
    
    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.EXCURSIONS_GROUP_SELECT_DATE, F.data.startswith("date:"))
async def select_group_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для групповых экскурсий"""
    await callback.answer()
    
    date = callback.data.split(":")[1]
    data = await state.get_data()
    island = data.get("island")
    
    # Получаем экскурсии на эту дату
    excursions = data_loader.get_excursions_by_filters(
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
    await show_group_excursion(callback.message, state, 0, date)


async def show_group_excursion(message: Message, state: FSMContext, index: int, current_date: str):
    """Показать карточку групповой экскурсии"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    
    if not excursions or index >= len(excursions):
        return
    
    excursion = excursions[index]
    card_text = get_group_excursion_card_text(excursion)
    
    # Проверяем наличие других экскурсий на эту же дату (для пагинации)
    has_prev = index > 0
    has_next = index < len(excursions) - 1
    
    # Создаем клавиатуру с пагинацией между экскурсиями
    buttons = []
    
    # Кнопка присоединиться
    buttons.append([InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"exc_join:{excursion['id']}")])
    
    # Пагинация между экскурсиями на одну дату
    if has_prev or has_next:
        nav_buttons = []
        if has_prev:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"exc_group_nav:prev:{index}"))
        if has_next:
            nav_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"exc_group_nav:next:{index}"))
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        card_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("exc_group_nav:"))
async def navigate_group_excursions(callback: CallbackQuery, state: FSMContext):
    """Навигация между групповыми экскурсиями на одну дату"""
    await callback.answer()
    
    parts = callback.data.split(":")
    direction = parts[1]
    current_index = int(parts[2])
    
    new_index = current_index - 1 if direction == "prev" else current_index + 1
    
    await state.update_data(current_excursion_index=new_index)
    
    data = await state.get_data()
    current_date = data.get("current_date")
    
    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем новую экскурсию
    await show_group_excursion(callback.message, state, new_index, current_date)


@router.callback_query(F.data.startswith("exc_join:"))
async def join_group_excursion(callback: CallbackQuery, state: FSMContext):
    """Присоединиться к групповой экскурсии"""
    await callback.answer()
    
    excursion_id = callback.data.split(":")[1]
    excursion = data_loader.get_excursion_by_id(excursion_id)
    
    if not excursion:
        return
    
    await state.update_data(selected_excursion_id=excursion_id)
    
    await callback.message.answer(
        get_excursion_join_text(excursion["name"]),
        reply_markup=get_share_contact_keyboard()
    )
    
    await state.set_state(UserStates.SHARE_CONTACT)


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
        excursions = data_loader.get_excursions_by_filters(
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


async def show_private_excursion(message: Message, state: FSMContext, index: int):
    """Показать карточку индивидуальной экскурсии"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("people_count", 1)
    
    if not excursions or index >= len(excursions):
        return
    
    excursion = excursions[index]
    card_text = get_private_excursion_card_text(excursion, people_count)
    
    keyboard = get_private_excursion_keyboard(
        excursion["id"],
        index,
        len(excursions)
    )
    
    await message.answer(
        card_text,
        reply_markup=keyboard
    )


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
    calendar = get_calendar_keyboard(now.year, now.month)
    
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
    calendar = get_calendar_keyboard(year, month)
    
    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.EXCURSIONS_PRIVATE_SELECT_DATE, F.data.startswith("date:"))
async def select_private_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для индивидуальной экскурсии"""
    await callback.answer()
    
    date = callback.data.split(":")[1]
    
    data = await state.get_data()
    excursion_id = data.get("selected_excursion_id")
    people_count = data.get("people_count")
    
    excursion = data_loader.get_excursion_by_id(excursion_id)
    
    if not excursion:
        return
    
    await callback.message.edit_text(
        get_excursion_booking_text(excursion["name"], people_count, format_date(date)),
        reply_markup=get_share_contact_keyboard()
    )
    
    await state.set_state(UserStates.SHARE_CONTACT)


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
    excursions = data_loader.get_companions_by_month(island, year, month)
    
    await state.update_data(
        companions_month=month, 
        companions_year=year,
        companions_excursions=excursions
    )
    
    if not excursions:
        text = f"На выбранный месяц экскурсий с поиском попутчиков пока нет."
        keyboard = get_companions_list_keyboard(month, year)
        
        await message.answer(text, reply_markup=keyboard)
    else:
        # Показываем каждую экскурсию с кнопкой
        text = "**Экскурсии с поиском попутчиков:**\n\n"
        await message.answer(text, parse_mode="Markdown")
        
        for i, exc in enumerate(excursions):
            card_text = f"📅 {format_date(exc['date'])}, {exc['time']}\n"
            card_text += f"{exc['name']}\n"
            card_text += f"👥 Уже {exc['companions_count']} человек"
            
            # Кнопка для просмотра детальной информации
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Подробнее", callback_data=f"comp_view:{exc['id']}")]
            ])
            
            await message.answer(card_text, reply_markup=keyboard)
        
        # Навигация в конце
        nav_keyboard = get_companions_list_keyboard(month, year)
        await message.answer("Навигация:", reply_markup=nav_keyboard)


@router.callback_query(UserStates.COMPANIONS_VIEW_LIST, F.data.startswith("comp_month:"))
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
    excursions = data_loader.get_excursions_by_filters(island=island)
    
    if not excursions:
        await callback.message.edit_text(
            "😔 К сожалению, экскурсий не найдено.",
            reply_markup=get_back_to_main_keyboard()
        )
        return
    
    # Формируем список экскурсий
    text = COMPANIONS_SELECT_EXCURSION + "\n\n"
    for i, exc in enumerate(excursions, 1):
        text += f"{i}. {exc['name']}\n"
    
    await state.update_data(available_excursions=excursions)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_main_keyboard()
    )
    
    await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)


@router.callback_query(F.data == "comp_create:agree")
async def create_companion_agree(callback: CallbackQuery, state: FSMContext):
    """Согласие с условиями поиска попутчиков"""
    await callback.answer()
    
    data = await state.get_data()
    island = data.get("island")
    
    # Получаем все экскурсии для выбора
    excursions = data_loader.get_excursions_by_filters(island=island)
    
    if not excursions:
        await callback.message.edit_text(
            "😔 К сожалению, экскурсий не найдено.",
            reply_markup=get_back_to_main_keyboard()
        )
        return
    
    # Формируем inline кнопки для каждой экскурсии
    buttons = []
    for exc in excursions:
        buttons.append([InlineKeyboardButton(
            text=exc['name'][:60],  # Обрезаем длинные названия
            callback_data=f"comp_select_exc:{exc['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="comp_back:list")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        COMPANIONS_SELECT_EXCURSION,
        reply_markup=keyboard
    )
    
    await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION, F.data.startswith("comp_select_exc:"))
async def select_excursion_for_companion(callback: CallbackQuery, state: FSMContext):
    """Выбор экскурсии для создания заявки"""
    await callback.answer()
    
    excursion_id = callback.data.split(":")[1]
    await state.update_data(selected_excursion_id=excursion_id)
    
    # Показываем календарь
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month)
    
    await callback.message.edit_text(
        COMPANIONS_SELECT_DATE,
        reply_markup=calendar
    )
    
    await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_DATE)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_DATE, F.data.startswith("cal:"))
async def navigate_companion_calendar(callback: CallbackQuery):
    """Навигация по календарю для создания заявки"""
    await callback.answer()
    
    date_str = callback.data.split(":")[1]
    
    if date_str == "ignore":
        return
    
    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month)
    
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
        
        excursion = data_loader.get_excursion_by_id(excursion_id)
        
        if not excursion:
            return
        
        await state.update_data(people_count=people_count)
        
        # Показываем подтверждение
        await message.answer(
            get_companions_created_text(excursion["name"], format_date(date), people_count),
            reply_markup=get_share_contact_keyboard()
        )
        
        await state.set_state(UserStates.SHARE_CONTACT)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число",
            reply_markup=get_back_to_main_keyboard()
        )


# ========== Обработка контактов для экскурсий ==========

@router.message(UserStates.SHARE_CONTACT, F.text)
async def process_excursion_phone(message: Message, state: FSMContext):
    """Обработка номера телефона для экскурсий"""
    valid, phone_number = validate_phone_number(message.text)
    
    if not valid:
        await message.answer(
            "❌ Неверный формат номера телефона.\n\nПожалуйста, введите номер в формате:\n+79991234567 или 89991234567",
            reply_markup=get_back_to_main_keyboard()
        )
        return
    
    try:
        await message.delete()
    except:
        pass
    
    await state.update_data(phone_number=phone_number)
    
    await message.answer(
        CONTACT_RECEIVED,
        reply_markup=get_back_to_main_keyboard()
    )
    
    await state.set_state(UserStates.MAIN_MENU)


@router.message(UserStates.SHARE_CONTACT, F.contact)
async def process_excursion_contact(message: Message, state: FSMContext):
    """Обработка контакта для экскурсий"""
    phone_number = message.contact.phone_number
    
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    await state.update_data(phone_number=phone_number)
    
    await message.answer(
        CONTACT_RECEIVED,
        reply_markup=get_back_to_main_keyboard()
    )
    
    await state.set_state(UserStates.MAIN_MENU)


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
    """Просмотр деталей экскурсии"""
    await callback.answer("🔍 Функция просмотра экскурсии будет реализована позже", show_alert=True)