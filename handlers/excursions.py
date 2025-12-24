"""Обработчики флоу экскурсий"""
import logging
import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
    get_back_to_main_keyboard,
    get_all_locations_keyboard,
    get_group_excursion_full_keyboard,
    get_action_choice_keyboard,
    get_group_month_excursion_detail_keyboard,
    get_month_excursions_list_keyboard
)
from handlers.main_menu import show_main_menu
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
    format_date,
    send_items_page,
    send_excursion_card_with_photo
)
from utils.data_loader import get_data_loader
from utils.media_manager import get_excursion_photo
from utils.contact_handler import contact_handler
from utils.order_manager import order_manager

router = Router()

EXCURSIONS_PER_PAGE = 5
MAX_EXCURSION_NAME_LENGTH = 40

# Названия месяцев в именительном и родительном падежах
MONTH_NAMES = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

MONTH_NAMES_GENITIVE = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
]


# ========== Старт флоу экскурсий ==========

@router.callback_query(F.data == "main:excursions")
async def start_excursions_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу экскурсий - выбор острова"""
    await callback.answer()

    # Очищаем filtered_excursions если они остались от поиска
    await state.update_data(filtered_excursions=None, search_query=None)

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

    # Очищаем filtered_excursions если они остались от поиска
    await state.update_data(filtered_excursions=None, search_query=None)

    island_code = callback.data.split(":")[1]

    # ОПТИМИЗАЦИЯ: запускаем предзагрузку индивидуальных экскурсий в фоне (без await!)
    if island_code != "other":
        data_loader = get_data_loader()
        # Создаём задачу в фоне, не ждём её завершения
        asyncio.create_task(data_loader.excursions_loader.preload_private_excursions(island=island_code))

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
                "Выберите остров для поиска экскурсий:",
                reply_markup=get_all_locations_keyboard(locations, page=0),
                parse_mode="Markdown"
            )

            await state.set_state(UserStates.EXCURSIONS_SELECT_OTHER_LOCATION)

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки локаций для экскурсий: {e}")
            await loading_msg.edit_text(
                "😔 Произошла ошибка при загрузке списка островов.",
                reply_markup=get_back_to_main_keyboard()
            )
        return

    await state.update_data(island=island_code)

    await callback.message.edit_text(
        EXCURSIONS_SELECT_TYPE,
        reply_markup=get_excursion_type_keyboard()
    )

    await state.set_state(UserStates.EXCURSIONS_SELECT_TYPE)


# ========== Обработчики для "Других островов" в экскурсиях ==========

@router.callback_query(UserStates.EXCURSIONS_SELECT_OTHER_LOCATION, F.data.startswith("location:"))
async def select_other_location_for_excursions(callback: CallbackQuery, state: FSMContext):
    """Выбор локации из полного списка для экскурсий"""
    await callback.answer()

    location_code = callback.data.split(":")[1]

    # Сохраняем выбранную локацию
    await state.update_data(island=location_code)

    await callback.message.edit_text(
        EXCURSIONS_SELECT_TYPE,
        reply_markup=get_excursion_type_keyboard()
    )

    await state.set_state(UserStates.EXCURSIONS_SELECT_TYPE)


@router.callback_query(UserStates.EXCURSIONS_SELECT_OTHER_LOCATION, F.data.startswith("locations_page:"))
async def navigate_locations_page_for_excursions(callback: CallbackQuery, state: FSMContext):
    """Навигация по страницам локаций для экскурсий"""
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
        "Выберите остров для поиска экскурсий:",
        reply_markup=get_all_locations_keyboard(locations, page=page),
        parse_mode="Markdown"
    )


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
    excursions = await get_data_loader().get_excursions_by_filters(
        island=island,
        excursion_type="group",
        date=date
    )
    
    if not excursions:
        await callback.message.edit_text(
            NO_EXCURSIONS_FOUND,
            reply_markup=get_no_group_excursions_keyboard(selected_date=date)
        )
        await state.update_data(current_date=date)
        return
    
    # Сохраняем данные
    await state.update_data(
        excursions=excursions,
        current_date=date,
        current_excursion_index=0
    )
    
    # Удаляем сообщение с календарем
    await callback.message.delete()

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
    current_date = data.get("current_date")

    # Используем клавиатуру из keyboards
    keyboard = get_group_excursion_full_keyboard(
        excursion_id=excursion['id'],
        index=index,
        has_prev=has_prev,
        has_next=has_next,
        current_date=current_date,
        expanded=expanded
    )

    # Используем универсальную функцию отправки
    await send_excursion_card_with_photo(message, card_text, keyboard, excursion["id"])


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
    current_date = data.get("current_date")

    # Используем клавиатуру из keyboards
    keyboard = get_group_excursion_full_keyboard(
        excursion_id=excursion['id'],
        index=index,
        has_prev=has_prev,
        has_next=has_next,
        current_date=current_date,
        expanded=expanded
    )

    # Удаляем старое сообщение
    await callback.message.delete()

    # Используем универсаль��ую функцию отправки
    await send_excursion_card_with_photo(callback.message, card_text, keyboard, excursion["id"])


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
    await callback.message.delete()

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


async def send_private_excursions_cards_page(message: Message, state: FSMContext, page: int):
    """Отправить страницу с приватными экскурсиями (по 5 штук)"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("people_count", 1)

    if not excursions:
        return

    # Функция форматирования карточки
    def format_card(excursion):
        return get_private_excursion_card_text(excursion, people_count, expanded=False)

    # Функция создания клавиатуры
    def get_keyboard(excursion):
        buttons = [
            [InlineKeyboardButton(text="✅ Забронировать", callback_data=f"exc_book:{excursion['id']}")],
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
        callback_prefix="exc_private_cards_page",
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


@router.callback_query(F.data == "exc_group_month:back")
async def back_to_group_month_list(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку экскурсий за месяц"""
    await callback.answer()

    data = await state.get_data()
    year = data.get("group_month_year")
    month = data.get("group_month_month")
    page = data.get("group_month_page", 0)

    try:
        await callback.message.delete()
    except:
        pass

    await show_group_month_excursions_list(callback.message, state, year, month, page=page)


@router.callback_query(F.data.startswith("exc_group_month:"))
async def show_group_month_excursions(callback: CallbackQuery, state: FSMContext):
    """Показать все групповые экскурсии за месяц"""
    await callback.answer()

    month_str = callback.data.split(":")[1]
    year, month = map(int, month_str.split("-"))

    data = await state.get_data()
    island = data.get("island")

    # ИСПРАВЛЕНИЕ: Для групповых экскурсий за месяц нужно получить все события
    # через обычный календарный API, а не через get_companions_by_month,
    # который фильтрует только индивидуальные (group_ex == 0).
    # Получаем все групповые экскурсии без фильтрации по дате
    all_excursions = await get_data_loader().get_excursions_by_filters(
        island=island,
        excursion_type="group",
        date=None  # Без даты - получаем весь календарь
    )

    # Фильтруем только экскурсии за нужный месяц/год
    excursions = []
    for exc in all_excursions:
        exc_date = exc.get("date")  # "YYYY-MM-DD"
        if exc_date:
            try:
                exc_dt = datetime.strptime(exc_date, "%Y-%m-%d")
                if exc_dt.year == year and exc_dt.month == month:
                    excursions.append(exc)
            except:
                pass

    if not excursions:
        await callback.answer(f"На {MONTH_NAMES_GENITIVE[month-1]} экскурсий не найдено", show_alert=True)
        return

    # Сохраняем данные
    await state.update_data(
        group_month_excursions=excursions,
        group_month_year=year,
        group_month_month=month,
        group_month_page=0
    )

    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем первую страницу
    await show_group_month_excursions_list(callback.message, state, year, month, page=0)


async def show_group_month_excursions_list(message: Message, state: FSMContext, year: int, month: int, page: int = 0):
    """Показать список групповых экскурсий за месяц с постраничным выводом"""
    data = await state.get_data()

    # ИСПРАВЛЕНО: Используем уже загруженные данные из state вместо повторной загрузки
    excursions = data.get("group_month_excursions", [])

    # Обновляем только страницу
    await state.update_data(group_month_page=page)

    # Формируем текст заголовка
    text = f"**Групповые экскурсии**\n{MONTH_NAMES[month-1]} {year}\n\n"

    if not excursions:
        text += "На выбранный месяц экскурсий пока нет."
        buttons = [
            [InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_type")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        # Постраничный вывод
        total_excursions = len(excursions)
        total_pages = (total_excursions + EXCURSIONS_PER_PAGE - 1) // EXCURSIONS_PER_PAGE

        # Нормализуем номер страницы
        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1

        # Получаем экскурсии для текущей страницы
        start_idx = page * EXCURSIONS_PER_PAGE
        end_idx = min(start_idx + EXCURSIONS_PER_PAGE, total_excursions)
        page_excursions = excursions[start_idx:end_idx]

        text += f"Показаны экскурсии {start_idx + 1}-{end_idx} из {total_excursions}\n\n"

        # Используем универсальную клавиатуру
        keyboard = get_month_excursions_list_keyboard(
            excursions=page_excursions,
            page=page,
            total_pages=total_pages,
            year=year,
            month=month,
            view_callback_prefix="exc_group_month_view",
            page_callback_prefix="exc_group_month_page",
            month_callback_prefix="exc_group_month",
            show_create_button=False,
            max_name_length=MAX_EXCURSION_NAME_LENGTH
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("exc_group_month_page:"))
async def navigate_group_month_page(callback: CallbackQuery, state: FSMContext):
    """Навигация по страницам экскурсий за месяц"""
    await callback.answer()

    page_str = callback.data.split(":")[1]

    if page_str == "ignore":
        return

    page = int(page_str)
    data = await state.get_data()
    year = data.get("group_month_year")
    month = data.get("group_month_month")

    try:
        await callback.message.delete()
    except:
        pass

    await show_group_month_excursions_list(callback.message, state, year, month, page=page)


@router.callback_query(F.data.startswith("exc_group_month_view:"))
async def view_group_month_excursion(callback: CallbackQuery, state: FSMContext):
    """Просмотр детальной информации об экскурсии из месячного списка"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]

    # Сначала пробуем найти экскурсию в уже загруженных данных (с датой)
    data = await state.get_data()
    group_month_excursions = data.get("group_month_excursions", [])

    excursion = None
    for exc in group_month_excursions:
        if exc.get("id") == excursion_id:
            excursion = exc
            break

    # Если не нашли - загружаем из API (но дата может быть некорректной)
    if not excursion:
        excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    # Показываем детальную карточку
    card_text = get_group_excursion_card_text(excursion, expanded=False)
    keyboard = get_group_month_excursion_detail_keyboard(excursion['id'])

    # Используем универсальную функцию отправки
    await send_excursion_card_with_photo(callback.message, card_text, keyboard, excursion["id"])


@router.callback_query(F.data.startswith("exc_join:"))
async def join_group_excursion(callback: CallbackQuery, state: FSMContext):
    """Присоединиться к групповой экскурсии"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]
    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    # ВАЖНО: Сохраняем дату экскурсии для последующего добавления в заказ
    excursion_date = excursion.get("date")
    await state.update_data(
        selected_excursion_id=excursion_id,
        excursion_people_count=1,
        excursion_date=excursion_date
    )

    # Используем универсальную клавиатуру
    keyboard = get_action_choice_keyboard("group")

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

        # Показываем сообщение о загрузке
        loading_msg = await message.answer("⏳ Загружаю индивидуальные экскурсии...")

        # Получаем индивидуальные экскурсии
        excursions = await get_data_loader().get_excursions_by_filters(
            island=island,
            excursion_type="private"
        )

        # Удаляем сообщение о загрузке
        try:
            await loading_msg.delete()
        except:
            pass

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

    # Telegram ограничивает caption до 1024 символов
    MAX_CAPTION_LENGTH = 1024
    if len(card_text) > MAX_CAPTION_LENGTH:
        card_text = card_text[:MAX_CAPTION_LENGTH - 3] + "..."

    if photo:
        try:
            await message.answer_photo(
                photo=photo,
                caption=card_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить фото для экскурсии: {e}")
            # Если не удалось отправить с фото - отправляем без фото
            await message.answer(
                card_text,
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


@router.callback_query(F.data == "exc_private:show_all")
async def show_all_private_excursions(callback: CallbackQuery, state: FSMContext):
    """Показать все приватные экскурсии страницей"""
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
    await send_private_excursions_cards_page(callback.message, state, page=1)


@router.callback_query(F.data.startswith("exc_private_cards_page:"))
async def navigate_private_excursions_pages(callback: CallbackQuery, state: FSMContext):
    """Переключение страниц приватных экскурсий"""
    await callback.answer()

    # Получаем номер страницы
    page = int(callback.data.split(":")[1])

    # Удаляем контрольное сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем новую страницу
    await send_private_excursions_cards_page(callback.message, state, page)


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

    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    await state.update_data(excursion_people_count=people_count)

    # Используем универсальную клавиатуру
    keyboard = get_action_choice_keyboard("private")

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


async def show_companions_list(message: Message, state: FSMContext, year: int, month: int, page: int = 0):
    """Показать список экскурсий с поиском попутчиков"""
    data = await state.get_data()
    island = data.get("island")

    # Получаем экскурсии за месяц
    excursions = await get_data_loader().get_companions_by_month(island, year, month)
    
    await state.update_data(
        companions_month=month,
        companions_year=year,
        companions_excursions=excursions,
        companions_page=page
    )

    # Формируем текст заголовка
    text = f"**Экскурсии с поиском попутчиков**\n{MONTH_NAMES[month-1]} {year}\n\n"

    if not excursions:
        text += "На выбранный месяц экскурсий пока нет."
        keyboard = get_companions_list_keyboard(month, year)

        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        # Постраничный вывод
        total_excursions = len(excursions)
        total_pages = (total_excursions + EXCURSIONS_PER_PAGE - 1) // EXCURSIONS_PER_PAGE

        # Нормализуем номер страницы
        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1

        # Получаем экскурсии для текущей страницы
        start_idx = page * EXCURSIONS_PER_PAGE
        end_idx = min(start_idx + EXCURSIONS_PER_PAGE, total_excursions)
        page_excursions = excursions[start_idx:end_idx]

        text += f"Показаны экскурсии {start_idx + 1}-{end_idx} из {total_excursions}\n\n"

        # Используем универсальную клавиатуру
        keyboard = get_month_excursions_list_keyboard(
            excursions=page_excursions,
            page=page,
            total_pages=total_pages,
            year=year,
            month=month,
            view_callback_prefix="comp_view",
            page_callback_prefix="comp_page",
            month_callback_prefix="comp_month",
            show_create_button=True,
            max_name_length=MAX_EXCURSION_NAME_LENGTH
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("comp_view:"))
async def view_companion_excursion(callback: CallbackQuery, state: FSMContext):
    """Просмотр детальной информации об экскурсии с попутчиками"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]

    # ИСПРАВЛЕНО: Всегда загружаем полные данные с API для получения списка попутчиков (slst)
    # Краткий список содержит только базовую информацию без контактов участников
    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        # Если не удалось загрузить из API, пробуем взять из кэша
        data = await state.get_data()
        companions_excursions = data.get("companions_excursions", [])
        for exc in companions_excursions:
            if exc.get("id") == excursion_id:
                excursion = exc
                break

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
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
    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    await state.update_data(selected_excursion_id=excursion_id, excursion_people_count=1)

    # Используем универсальную клавиатуру
    keyboard = get_action_choice_keyboard("companion")

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
    page = data.get("companions_page", 0)

    try:
        await callback.message.delete()
    except:
        pass

    await show_companions_list(callback.message, state, year, month, page=page)

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

    await show_companions_list(callback.message, state, year, month, page=0)


@router.callback_query(F.data.startswith("comp_page:"))
async def navigate_companions_page(callback: CallbackQuery, state: FSMContext):
    """Навигация по страницам экскурсий с попутчиками"""
    await callback.answer()

    page_str = callback.data.split(":")[1]

    if page_str == "ignore":
        return

    page = int(page_str)
    data = await state.get_data()
    year = data.get("companions_year")
    month = data.get("companions_month")

    try:
        await callback.message.delete()
    except:
        pass

    await show_companions_list(callback.message, state, year, month, page=page)


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
    """Согласие с условиями поиска попутчиков - запрашиваем количество человек"""
    await callback.answer()

    # Запрашиваем количество человек (как в ветке индивидуальных экскурсий)
    await callback.message.edit_text(
        COMPANIONS_INPUT_PEOPLE,
        reply_markup=get_back_to_main_keyboard()
    )

    await state.set_state(UserStates.COMPANIONS_CREATE_INPUT_PEOPLE)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION, F.data.startswith("exc_nav:"))
async def navigate_companion_excursions(callback: CallbackQuery, state: FSMContext):
    """Навигация по индивидуальным экскурсиям при создании заявки"""
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


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION, F.data.startswith("exc_book:"))
async def select_excursion_for_companion(callback: CallbackQuery, state: FSMContext):
    """Выбор экскурсии для создания заявки - показываем календарь"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]
    await state.update_data(selected_excursion_id=excursion_id)

    # Показываем календарь выбора даты
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month, back_callback="excursions:back_companion_from_calendar")

    await callback.message.answer(
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
    calendar = get_calendar_keyboard(year, month, back_callback="excursions:back_companion_from_calendar")

    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_DATE, F.data.startswith("date:"))
async def select_date_for_companion(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для заявки - запрашиваем контакт"""
    await callback.answer()

    date = callback.data.split(":")[1]

    data = await state.get_data()
    excursion_id = data.get("selected_excursion_id")
    people_count = data.get("people_count")

    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    await state.update_data(
        companion_date=date,
        excursion_people_count=people_count
    )

    # Запрашиваем контакт для создания заявки
    await callback.message.edit_text(
        f"Отлично! Вы создаете заявку на поиск попутчиков:\n\n"
        f"**{excursion['name']}**\n"
        f"📅 Дата: {format_date(date)}\n"
        f"👥 Количество человек: {people_count}\n\n"
        f"Для создания заявки поделитесь своими контактными данными.\n\n"
        f"Наш менеджер свяжется с вами для подтверждения.",
        reply_markup=get_share_contact_keyboard(),
        parse_mode="Markdown"
    )

    await state.set_state(UserStates.SHARE_CONTACT)


@router.message(UserStates.COMPANIONS_CREATE_INPUT_PEOPLE, F.text)
async def process_companion_people_count(message: Message, state: FSMContext):
    """Обработка количества человек для заявки - загружаем и показываем индивидуальные экскурсии"""
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

        # Показываем сообщение о загрузке
        loading_msg = await message.answer("⏳ Загружаю индивидуальные экскурсии...")

        # ИСПРАВЛЕНО: Получаем ТОЛЬКО индивидуальные экскурсии (как в ветке private)
        excursions = await get_data_loader().get_excursions_by_filters(
            island=island,
            excursion_type="private"
        )

        # Удаляем сообщение о загрузке
        try:
            await loading_msg.delete()
        except:
            pass

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

        # Показываем первую экскурсию (используем функцию из ветки private)
        await show_private_excursion(message, state, 0)

        await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)

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

    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    # Добавляем в заказ
    updated_data = order_manager.add_excursion(data, excursion, people_count)
    await state.update_data(order=updated_data["order"])

    # Возвращаем в главное меню
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

    # ВАЖНО: Добавляем экскурсию в корзину ПЕРЕД запросом контакта
    data = await state.get_data()
    excursion_id = data.get("selected_excursion_id")
    people_count = data.get("excursion_people_count", 1)

    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    # Добавляем в заказ
    updated_data = order_manager.add_excursion(data, excursion, people_count)
    await state.update_data(order=updated_data["order"])

    await callback.message.edit_text(
        "Для бронирования поделитесь своими контактными данными.\n\nНаш менеджер свяжется с вами для подтверждения.",
        reply_markup=get_share_contact_keyboard()
    )

    await state.set_state(UserStates.SHARE_CONTACT)


# ========== Обработка контактов для экскурсий ==========

@router.message(UserStates.SHARE_CONTACT, F.text)
async def process_excursion_phone(message: Message, state: FSMContext):
    """Обработка номера телефона для экскурсий"""
    if await contact_handler.process_text_phone(message, state):
        from handlers.order import finalize_order
        await finalize_order(message, state)


@router.message(UserStates.SHARE_CONTACT, F.contact)
async def process_excursion_contact(message: Message, state: FSMContext):
    """Обработка контакта для экскурсий"""
    if await contact_handler.process_contact(message, state):
        from handlers.order import finalize_order
        await finalize_order(message, state)


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
    """Назад из календаря создания заявки попутчиков - возвращаемся к карточкам"""
    await callback.answer()

    # Удаляем календарь
    try:
        await callback.message.delete()
    except:
        pass

    # Возвращаемся к карточкам индивидуальных экскурсий
    data = await state.get_data()
    current_index = data.get("current_excursion_index", 0)

    await show_private_excursion(callback.message, state, current_index)

    await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)