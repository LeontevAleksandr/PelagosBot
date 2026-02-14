"""Обработчики индивидуальных экскурсий"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

logger = logging.getLogger(__name__)

from states.user_states import UserStates
from keyboards import (
    get_back_to_main_keyboard,
    get_private_islands_keyboard,
    get_private_excursion_keyboard,
    get_action_choice_keyboard
)
from utils.texts import EXCURSIONS_PRIVATE_INTRO, get_private_excursion_card_text, get_excursion_booking_text
from utils.data_loader import get_data_loader
from utils.helpers import format_date, get_calendar_keyboard, send_items_page
from utils.media_manager import get_excursion_photo
from handlers.excursions.common import EXCURSIONS_PER_PAGE

router = Router()

# ========== Выбор острова и количества людей ==========

@router.callback_query(UserStates.EXCURSIONS_SELECT_TYPE, F.data == "exc_type:private")
async def select_private_excursions(callback: CallbackQuery, state: FSMContext):
    """Выбор индивидуальных экскурсий - показываем выбор острова"""
    await callback.answer()

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.edit_text("⏳ Загружаю доступные острова с экскурсиями...")

    try:
        # Загружаем все острова с подсчётом экскурсий
        islands = await get_data_loader().excursions_loader.get_available_islands_with_count()

        if not islands:
            await loading_msg.edit_text(
                "😔 К сожалению, не удалось загрузить список островов с экскурсиями. Попробуйте позже.",
                reply_markup=get_back_to_main_keyboard()
            )
            return

        # Показываем клавиатуру выбора острова
        await loading_msg.edit_text(
            f"**Индивидуальные экскурсии**\n\n"
            f"Выберите остров для поиска экскурсий:\n"
            f"_(Всего найдено {len(islands)} островов с экскурсиями)_",
            reply_markup=get_private_islands_keyboard(islands),
            parse_mode="Markdown"
        )

        await state.set_state(UserStates.EXCURSIONS_PRIVATE_SELECT_ISLAND)

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки островов для индивидуальных экскурсий: {e}")
        await loading_msg.edit_text(
            "😔 Произошла ошибка при загрузке списка островов.",
            reply_markup=get_back_to_main_keyboard()
        )


@router.callback_query(UserStates.EXCURSIONS_PRIVATE_SELECT_ISLAND, F.data.startswith("private_island:"))
async def select_private_island(callback: CallbackQuery, state: FSMContext):
    """Выбор острова для индивидуальных экскурсий - запрашиваем количество людей"""
    await callback.answer()

    location_id = int(callback.data.split(":")[1])

    # Сохраняем location_id как island в state (для совместимости с существующим кодом)
    await state.update_data(island=str(location_id))

    # Запрашиваем количество человек с клавиатурой
    from handlers.excursions.common import get_people_count_keyboard
    await callback.message.edit_text(
        EXCURSIONS_PRIVATE_INTRO,
        reply_markup=get_people_count_keyboard()
    )

    await state.set_state(UserStates.EXCURSIONS_PRIVATE_INPUT_PEOPLE)


# ========== Отображение карточек экскурсий ==========

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


# ========== Постраничный вывод всех экскурсий ==========

@router.callback_query(F.data == "exc_private:show_all")
async def show_all_private_excursions(callback: CallbackQuery, state: FSMContext):
    """Показать все приватные экскурсии страницей"""
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
        await send_private_excursions_cards_page(callback.message, state, page=1)

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

    # Функция создания клавиатуры с кнопками развернуть/свернуть и ссылкой
    def get_keyboard(excursion):
        buttons = [
            [InlineKeyboardButton(text="✅ Забронировать", callback_data=f"exc_book:{excursion['id']}")],
            [InlineKeyboardButton(text="Развернуть ▼", callback_data=f"exc_private_expand_page:{excursion['id']}:{page}")],
        ]

        # Добавляем кнопку "Смотреть экскурсию" если есть URL
        excursion_url = excursion.get("url")
        if excursion_url:
            buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", url=excursion_url)])

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


@router.callback_query(F.data.startswith("exc_private_expand_page:"))
async def expand_private_excursion_in_page(callback: CallbackQuery, state: FSMContext):
    """Развернуть описание экскурсии в постраничном выводе"""
    await callback.answer()

    parts = callback.data.split(":")
    excursion_id = parts[1]
    page = int(parts[2])

    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("people_count", 1)

    # Находим экскурсию по ID
    excursion = None
    for exc in excursions:
        if exc.get("id") == excursion_id:
            excursion = exc
            break

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    # Формируем развернутый текст
    card_text = get_private_excursion_card_text(excursion, people_count, expanded=True)

    # Создаем клавиатуру с кнопкой "Свернуть"
    buttons = [
        [InlineKeyboardButton(text="✅ Забронировать", callback_data=f"exc_book:{excursion['id']}")],
        [InlineKeyboardButton(text="Свернуть ▲", callback_data=f"exc_private_collapse_page:{excursion['id']}:{page}")],
    ]

    # Добавляем кнопку "Смотреть экскурсию" если есть URL
    excursion_url = excursion.get("url")
    if excursion_url:
        buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", url=excursion_url)])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Обновляем сообщение
    try:
        await callback.message.edit_caption(
            caption=card_text,
            reply_markup=keyboard
        )
    except:
        # Если нет фото, пробуем обновить текст
        try:
            await callback.message.edit_text(
                text=card_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения: {e}")


@router.callback_query(F.data.startswith("exc_private_collapse_page:"))
async def collapse_private_excursion_in_page(callback: CallbackQuery, state: FSMContext):
    """Свернуть описание экскурсии в постраничном выводе"""
    await callback.answer()

    parts = callback.data.split(":")
    excursion_id = parts[1]
    page = int(parts[2])

    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("people_count", 1)

    # Находим экскурсию по ID
    excursion = None
    for exc in excursions:
        if exc.get("id") == excursion_id:
            excursion = exc
            break

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    # Формируем свернутый текст
    card_text = get_private_excursion_card_text(excursion, people_count, expanded=False)

    # Создаем клавиатуру с кнопкой "Развернуть"
    buttons = [
        [InlineKeyboardButton(text="✅ Забронировать", callback_data=f"exc_book:{excursion['id']}")],
        [InlineKeyboardButton(text="Развернуть ▼", callback_data=f"exc_private_expand_page:{excursion['id']}:{page}")],
    ]

    # Добавляем кнопку "Смотреть экскурсию" если есть URL
    excursion_url = excursion.get("url")
    if excursion_url:
        buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", url=excursion_url)])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Обновляем сообщение
    try:
        await callback.message.edit_caption(
            caption=card_text,
            reply_markup=keyboard
        )
    except:
        # Если нет фото, пробуем обновить текст
        try:
            await callback.message.edit_text(
                text=card_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения: {e}")


# ========== Бронирование индивидуальной экскурсии ==========

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
