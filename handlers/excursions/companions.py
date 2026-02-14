"""Обработчики поиска попутчиков"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime

logger = logging.getLogger(__name__)

from states.user_states import UserStates
from keyboards import (
    get_back_to_main_keyboard,
    get_private_islands_keyboard,
    get_companions_list_keyboard,
    get_month_excursions_list_keyboard,
    get_companions_excursion_keyboard,
    get_companions_create_agree_keyboard,
    get_action_choice_keyboard
)
from utils.texts import (
    COMPANIONS_INTRO,
    COMPANIONS_HOW_IT_WORKS,
    COMPANIONS_INPUT_PEOPLE,
    COMPANIONS_SELECT_DATE,
    get_companions_excursion_card_text
)
from utils.helpers import format_date, get_calendar_keyboard
from utils.data_loader import get_data_loader
from handlers.excursions.common import EXCURSIONS_PER_PAGE, MONTH_NAMES, get_people_count_keyboard

router = Router()

# ========== Просмотр списка попутчиков ==========

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
    # ИЗМЕНЕНО: Попутчики теперь загружаются БЕЗ фильтра по острову (все острова)
    # Получаем экскурсии за месяц
    excursions = await get_data_loader().get_companions_by_month(None, year, month)

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
        from handlers.excursions.common import MAX_EXCURSION_NAME_LENGTH
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
    logger.info(f"🔍 Просмотр попутчиков для экскурсии с event_id={excursion_id}")

    # ИСПРАВЛЕНО: Напрямую вызываем метод загрузки companion event
    excursion = await get_data_loader().excursions_loader.get_companion_event_by_id(excursion_id)

    if excursion:
        logger.info(f"✅ Экскурсия загружена: pax={excursion.get('pax', 0)}, companions={len(excursion.get('companions', []))}")

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
    """Присоединиться к экскурсии с попутчиками - запрашиваем количество людей"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]
    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    # Сохраняем ID экскурсии
    await state.update_data(selected_excursion_id=excursion_id)

    # Запрашиваем количество человек с клавиатурой
    await callback.message.answer(
        "Сколько человек присоединяется к экскурсии?",
        reply_markup=get_people_count_keyboard()
    )

    await state.set_state(UserStates.COMPANIONS_JOIN_INPUT_PEOPLE)


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


# ========== Создание заявки на попутчиков ==========

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

    # Запрашиваем количество человек с клавиатурой
    await callback.message.edit_text(
        COMPANIONS_INPUT_PEOPLE,
        reply_markup=get_people_count_keyboard()
    )

    await state.set_state(UserStates.COMPANIONS_CREATE_INPUT_PEOPLE)


@router.message(UserStates.COMPANIONS_CREATE_INPUT_PEOPLE, F.text)
async def process_companion_people_count(message: Message, state: FSMContext):
    """Обработка количества человек для заявки - показываем выбор острова"""
    try:
        people_count = int(message.text.strip())

        if people_count < 1:
            raise ValueError

        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass

        # Сохраняем количество людей
        await state.update_data(people_count=people_count)

        # Показываем сообщение о загрузке
        loading_msg = await message.answer("⏳ Загружаю доступные острова с экскурсиями...")

        try:
            # Загружаем все острова с подсчётом экскурсий (используем тот же метод что и для private)
            islands = await get_data_loader().excursions_loader.get_available_islands_with_count()

            if not islands:
                await loading_msg.edit_text(
                    "😔 К сожалению, не удалось загрузить список островов с экскурсиями. Попробуйте позже.",
                    reply_markup=get_back_to_main_keyboard()
                )
                return

            # Показываем клавиатуру выбора острова
            await loading_msg.edit_text(
                f"**Создание заявки на поиск попутчиков**\n\n"
                f"Выберите остров для поиска экскурсий:\n"
                f"_(Всего найдено {len(islands)} островов с экскурсиями)_",
                reply_markup=get_private_islands_keyboard(islands),
                parse_mode="Markdown"
            )

            await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_ISLAND)

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки островов для создания заявки на попутчиков: {e}")
            await loading_msg.edit_text(
                "😔 Произошла ошибка при загрузке списка островов.",
                reply_markup=get_back_to_main_keyboard()
            )

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число",
            reply_markup=get_back_to_main_keyboard()
        )


@router.callback_query(
    UserStates.COMPANIONS_CREATE_SELECT_ISLAND,
    F.data.startswith("private_island:")
)
async def select_companion_island(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора острова для создания заявки на попутчиков - загружаем экскурсии"""
    await callback.answer()

    location_id = int(callback.data.split(":")[1])

    # Сохраняем location_id как island в state
    await state.update_data(island=str(location_id))

    island = str(location_id)

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.edit_text("⏳ Загружаю индивидуальные экскурсии...")

    try:
        # Получаем ТОЛЬКО индивидуальные экскурсии для выбранного острова
        excursions = await get_data_loader().get_excursions_by_filters(
            island=island,
            excursion_type="private"
        )

        if not excursions:
            await loading_msg.edit_text(
                "😔 К сожалению, индивидуальных экскурсий на этом острове не найдено.",
                reply_markup=get_back_to_main_keyboard()
            )
            return

        await state.update_data(
            excursions=excursions,
            current_excursion_index=0
        )

        # Удаляем сообщение о загрузке
        try:
            await loading_msg.delete()
        except:
            pass

        # Показываем первую экскурсию (используем функцию из ветки private)
        from handlers.excursions.private import show_private_excursion
        await show_private_excursion(callback.message, state, 0)

        await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки экскурсий для острова {island}: {e}")
        await loading_msg.edit_text(
            "😔 Произошла ошибка при загрузке экскурсий.",
            reply_markup=get_back_to_main_keyboard()
        )


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

    from handlers.excursions.private import show_private_excursion
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
    """Выбор даты для заявки - показываем выбор действия"""
    await callback.answer()

    date = callback.data.split(":")[1]

    data = await state.get_data()
    excursion_id = data.get("selected_excursion_id")
    people_count = data.get("people_count")

    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    # Сохраняем данные в состоянии (для последующего использования)
    await state.update_data(
        companion_date=date,
        excursion_people_count=people_count
    )

    # Формируем текст с информацией об экскурсии
    text = (
        f"**{excursion['name']}**\n\n"
        f"📅 Дата: {format_date(date)}\n"
        f"👥 Количество человек: {people_count}\n\n"
        f"Что хотите сделать?"
    )

    # Показываем клавиатуру выбора действия (как для групповых экскурсий)
    keyboard = get_action_choice_keyboard("create")

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )
