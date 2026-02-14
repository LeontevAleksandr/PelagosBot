"""Общие функции, константы и вспомогательные утилиты для экскурсий"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime

logger = logging.getLogger(__name__)

from states.user_states import UserStates
from keyboards import (
    get_excursion_type_keyboard,
    get_back_to_main_keyboard,
    get_action_choice_keyboard,
    get_private_islands_keyboard
)
from utils.texts import EXCURSIONS_SELECT_TYPE
from utils.data_loader import get_data_loader

router = Router()

# ========== Константы ==========

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


# ========== Вспомогательные функции ==========

def get_people_count_keyboard():
    """Создать клавиатуру для выбора количества людей"""
    buttons = [
        [
            InlineKeyboardButton(text="1 человек", callback_data="people_count:1"),
            InlineKeyboardButton(text="2 человека", callback_data="people_count:2"),
            InlineKeyboardButton(text="3 человека", callback_data="people_count:3")
        ],
        [
            InlineKeyboardButton(text="4 человека", callback_data="people_count:4"),
            InlineKeyboardButton(text="5 и более", callback_data="people_count:5")
        ],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ========== Обработчик выбора количества людей ==========

@router.callback_query(F.data.startswith("people_count:"))
async def handle_people_count_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора количества людей через кнопки"""
    await callback.answer()

    count_str = callback.data.split(":")[1]

    # Сохраняем выбранное количество
    people_count = int(count_str)

    # Получаем текущее состояние для определения контекста
    current_state = await state.get_state()

    # В зависимости от текущего состояния выполняем соответствующую логику
    if current_state == UserStates.EXCURSIONS_GROUP_INPUT_PEOPLE:
        # Для групповых экскурсий - сохраняем количество и показываем список экскурсий
        # Цена фиксированная за человека, но показываем общую стоимость
        await state.update_data(
            excursion_people_count=people_count,
            current_excursion_index=0
        )

        # Показываем сообщение о загрузке
        loading_msg = await callback.message.edit_text("⏳ Подготавливаю экскурсии...")

        # Небольшая задержка для плавности UX
        try:
            await loading_msg.delete()
        except:
            pass

        # Показываем первую экскурсию с учетом количества людей
        from .group import show_group_excursion
        await show_group_excursion(callback.message, state, 0)

    elif current_state == UserStates.EXCURSIONS_PRIVATE_INPUT_PEOPLE:
        # Для индивидуальных экскурсий
        data = await state.get_data()
        island = data.get("island")

        loading_msg = await callback.message.edit_text("⏳ Загружаю индивидуальные экскурсии...")

        excursions = await get_data_loader().get_excursions_by_filters(
            island=island,
            excursion_type="private"
        )

        try:
            await loading_msg.delete()
        except:
            pass

        if not excursions:
            await callback.message.answer(
                "😔 К сожалению, индивидуальных экскурсий не найдено.",
                reply_markup=get_back_to_main_keyboard()
            )
            return

        await state.update_data(
            people_count=people_count,
            excursions=excursions,
            current_excursion_index=0
        )

        from .private import show_private_excursion
        await show_private_excursion(callback.message, state, 0)
        await state.set_state(UserStates.EXCURSIONS_SHOW_RESULTS)

    elif current_state == UserStates.COMPANIONS_JOIN_INPUT_PEOPLE:
        # Для присоединения к попутчикам
        await state.update_data(excursion_people_count=people_count)

        # Показываем сообщение о загрузке
        loading_msg = await callback.message.edit_text("⏳ Загружаю информацию об экскурсии...")

        data = await state.get_data()
        excursion_id = data.get("selected_excursion_id")
        excursion = await get_data_loader().get_excursion_by_id(excursion_id)

        if not excursion:
            await loading_msg.edit_text("❌ Ошибка: экскурсия не найдена")
            return

        from utils.texts import get_excursion_join_text
        keyboard = get_action_choice_keyboard("companion")
        await loading_msg.edit_text(
            get_excursion_join_text(excursion["name"]),
            reply_markup=keyboard
        )

    elif current_state == UserStates.COMPANIONS_CREATE_INPUT_PEOPLE:
        # Для создания заявки на попутчиков
        await state.update_data(people_count=people_count)

        loading_msg = await callback.message.edit_text("⏳ Загружаю доступные острова с экскурсиями...")

        try:
            islands = await get_data_loader().excursions_loader.get_available_islands_with_count()

            if not islands:
                await loading_msg.edit_text(
                    "😔 К сожалению, не удалось загрузить список островов с экскурсиями. Попробуйте позже.",
                    reply_markup=get_back_to_main_keyboard()
                )
                return

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

    elif current_state == UserStates.SEARCH_GROUP_INPUT_PEOPLE:
        # НОВОЕ: Для найденных через поиск групповых экскурсий
        await state.update_data(
            excursion_people_count=people_count,
            current_excursion_index=0
        )

        # Показываем сообщение о загрузке
        loading_msg = await callback.message.edit_text("⏳ Подготавливаю экскурсии...")

        try:
            await loading_msg.delete()
        except:
            pass

        # Переводим в состояние просмотра результатов
        await state.set_state(UserStates.EXCURSIONS_SHOW_RESULTS)

        # Показываем первую экскурсию с учетом количества людей
        from .group import show_group_excursion
        await show_group_excursion(callback.message, state, 0)

    elif current_state == UserStates.SEARCH_PRIVATE_INPUT_PEOPLE:
        # НОВОЕ: Для найденных через поиск индивидуальных экскурсий
        await state.update_data(
            people_count=people_count,
            current_excursion_index=0
        )

        # Показываем сообщение о загрузке
        loading_msg = await callback.message.edit_text("⏳ Загружаю экскурсии...")

        try:
            await loading_msg.delete()
        except:
            pass

        # Переводим в состояние просмотра результатов
        await state.set_state(UserStates.EXCURSIONS_SHOW_RESULTS)

        # Показываем первую страницу с экскурсиями
        from .private import send_private_excursions_cards_page
        await send_private_excursions_cards_page(callback.message, state, page=1)


# ========== Старт флоу экскурсий ==========

@router.callback_query(F.data == "main:excursions")
async def start_excursions_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу экскурсий - выбор типа экскурсии"""
    await callback.answer()

    # Очищаем filtered_excursions и island если они остались от предыдущих сессий
    await state.update_data(filtered_excursions=None, search_query=None, island=None)

    await callback.message.edit_text(
        EXCURSIONS_SELECT_TYPE,
        reply_markup=get_excursion_type_keyboard()
    )

    await state.set_state(UserStates.EXCURSIONS_SELECT_TYPE)
