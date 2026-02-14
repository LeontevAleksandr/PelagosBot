"""Обработчики навигации по флоу экскурсий"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

from states.user_states import UserStates
from keyboards import get_excursion_type_keyboard, get_back_to_main_keyboard
from utils.texts import EXCURSIONS_SELECT_TYPE

router = Router()

# ========== Навигация назад ==========

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

    from handlers.excursions.private import show_private_excursion
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

    from handlers.excursions.private import show_private_excursion
    await show_private_excursion(callback.message, state, current_index)

    await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)
