"""Обработчики бронирования и добавления экскурсий в заказ"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

from states.user_states import UserStates
from utils.data_loader import get_data_loader
from utils.order_manager import order_manager
from handlers.main_menu import show_main_menu
from utils.contact_handler import contact_handler

router = Router()

# ========== Добавление в заказ ==========

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


# ========== Бронирование сейчас ==========

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

    # Используем contact_handler для проверки сохранённого номера
    await contact_handler.request_phone(
        callback.message,
        state,
        "Для бронирования поделитесь своими контактными данными.\n\nНаш менеджер свяжется с вами для подтверждения."
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
