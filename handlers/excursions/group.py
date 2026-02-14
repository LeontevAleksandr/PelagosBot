"""Обработчики групповых экскурсий"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

logger = logging.getLogger(__name__)

from states.user_states import UserStates
from keyboards import (
    get_group_excursion_keyboard,
    get_no_group_excursions_keyboard,
    get_back_to_main_keyboard,
    get_group_excursion_full_keyboard,
    get_action_choice_keyboard,
    get_group_month_excursion_detail_keyboard,
    get_month_excursions_list_keyboard
)
from utils.texts import (
    EXCURSIONS_GROUP_INTRO,
    NO_EXCURSIONS_FOUND,
    get_group_excursion_card_text,
    get_excursion_booking_text
)
from utils.helpers import (
    get_calendar_keyboard,
    send_items_page,
    send_excursion_card_with_photo
)
from utils.data_loader import get_data_loader
from utils.media_manager import get_excursion_photo
from .common import (
    EXCURSIONS_PER_PAGE,
    MAX_EXCURSION_NAME_LENGTH,
    MONTH_NAMES,
    MONTH_NAMES_GENITIVE,
    get_people_count_keyboard
)

router = Router()


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

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.edit_text("⏳ Загружаю экскурсии на выбранную дату...")

    # Получаем экскурсии на эту дату
    all_excursions = await get_data_loader().get_excursions_by_filters(
        island=None,
        excursion_type="group",
        date=date
    )

    # ИСПРАВЛЕНИЕ: Фильтруем только экскурсии на выбранную дату
    # (API возвращает весь месяц, нужна дополнительная фильтрация)
    excursions = []
    for exc in all_excursions:
        exc_date = exc.get("date")  # "YYYY-MM-DD"
        if exc_date == date:
            excursions.append(exc)

    logger.info(f"🔍 Фильтрация по дате {date}: {len(all_excursions)} → {len(excursions)} экскурсий")

    if not excursions:
        await loading_msg.edit_text(
            NO_EXCURSIONS_FOUND,
            reply_markup=get_no_group_excursions_keyboard(selected_date=date)
        )
        await state.update_data(current_date=date)
        return

    # Дозагружаем цены для всех экскурсий (фиксированная цена за человека)
    logger.info(f"📊 Дозагрузка цен для {len(excursions)} групповых экскурсий...")
    for excursion in excursions:
        if not excursion.get('price_usd') or excursion.get('price_usd') == 0:
            # Загружаем полные данные экскурсии
            full_excursion = await get_data_loader().get_excursion_by_id(excursion['id'])
            if full_excursion and full_excursion.get('price_usd'):
                logger.info(f"   ✓ {excursion['name']}: ${full_excursion['price_usd']} за чел")
                excursion['price'] = full_excursion['price_usd']
                excursion['price_usd'] = full_excursion['price_usd']

    # Сохраняем экскурсии и дату
    await state.update_data(
        excursions=excursions,
        current_date=date
    )

    # Запрашиваем количество человек
    await loading_msg.edit_text(
        "Сколько вас человек собирается ехать (взрослые и дети старше 7 лет)?",
        reply_markup=get_people_count_keyboard()
    )
    await state.set_state(UserStates.EXCURSIONS_GROUP_INPUT_PEOPLE)


async def show_group_excursion(message: Message, state: FSMContext, index: int, expanded: bool = False):
    """Показать карточку групповой экскурсии"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("excursion_people_count", 1)

    if not excursions or index >= len(excursions):
        return

    excursion = excursions[index]
    card_text = get_group_excursion_card_text(excursion, people_count, expanded)

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
    people_count = data.get("excursion_people_count", 1)
    card_text = get_group_excursion_card_text(excursion, people_count, expanded=expanded)

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

    # Используем универсальную функцию отправки
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
    people_count = data.get("excursion_people_count", 1)

    if not excursions:
        return

    # Функция форматирования карточки
    def format_card(excursion):
        return get_group_excursion_card_text(excursion, people_count, expanded=False)

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

    # Удаляем текущее сообщение (может быть с фото)
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.answer("⏳ Загружаю экскурсии...")

    try:
        # Отправляем первую страницу
        await send_excursions_cards_page(callback.message, state, page=1)

        # Удаляем сообщение о загрузке
        try:
            await loading_msg.delete()
        except:
            pass
    except Exception as e:
        logger.error(f"Ошибка при отображении экскурсий: {e}")
        await loading_msg.edit_text(
            "😔 Произошла ошибка при загрузке экскурсий.",
            reply_markup=get_back_to_main_keyboard()
        )


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

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.answer(f"⏳ Загружаю экскурсии за {MONTH_NAMES[month-1]} {year}...")

    # Формируем дату первого дня месяца для запроса
    first_day_of_month = f"{year:04d}-{month:02d}-01"

    # Загружаем экскурсии, указав первый день месяца в запросе
    all_excursions = await get_data_loader().get_excursions_by_filters(
        island=None,  # Без фильтра по острову
        excursion_type="group",
        date=first_day_of_month  # Первый день месяца
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
        try:
            await loading_msg.delete()
        except:
            pass
        await callback.answer(f"На {MONTH_NAMES_GENITIVE[month-1]} экскурсий не найдено", show_alert=True)
        return

    # ИСПРАВЛЕНИЕ: Дозагружаем цены для всех экскурсий за месяц
    logger.info(f"📊 Дозагрузка цен для {len(excursions)} экскурсий за месяц...")
    for excursion in excursions:
        if not excursion.get('price_usd') or excursion.get('price_usd') == 0:
            # Загружаем полные данные экскурсии с ценой
            full_excursion = await get_data_loader().get_excursion_by_id(excursion['id'])
            if full_excursion and full_excursion.get('price_usd'):
                excursion['price'] = full_excursion['price_usd']
                excursion['price_usd'] = full_excursion['price_usd']

    # Сохраняем данные
    await state.update_data(
        group_month_excursions=excursions,
        group_month_year=year,
        group_month_month=month,
        group_month_page=0
    )

    # Удаляем сообщения о загрузке и текущее сообщение
    try:
        await loading_msg.delete()
    except:
        pass
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем первую страницу
    await show_group_month_excursions_list(callback.message, state, year, month, page=0)


async def show_group_month_excursions_list(message: Message, state: FSMContext, year: int, month: int, page: int = 0):
    """Показать список групповых экскурсий за месяц с постраничным выводом"""
    data = await state.get_data()

    # Используем уже загруженные данные из state вместо повторной загрузки
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
    people_count = data.get("excursion_people_count", 1)

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
    card_text = get_group_excursion_card_text(excursion, people_count, expanded=False)
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

    # Получаем количество людей из state (уже было введено ранее)
    data = await state.get_data()
    people_count = data.get("excursion_people_count", 1)

    # Сохраняем ID и дату экскурсии
    excursion_date = excursion.get("date")
    await state.update_data(
        selected_excursion_id=excursion_id,
        excursion_date=excursion_date
    )

    # Показываем форму для ввода контактных данных
    keyboard = get_action_choice_keyboard("group")
    await callback.message.answer(
        get_excursion_booking_text(excursion["name"], people_count, excursion_date),
        reply_markup=keyboard
    )
