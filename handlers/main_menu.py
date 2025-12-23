"""Обработчики главного меню"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from handlers.order import view_order

from keyboards import (
    get_menu_keyboard, 
    get_main_menu_keyboard,
    get_back_to_main_keyboard
)
from states.user_states import UserStates
from utils.texts import (
    MENU_TEXT, 
    MY_ORDERS_TEXT, 
    MY_ORDERS_EMPTY,
    get_main_menu_text
)
from database.db_crud import get_orders_for_user
from utils.contact_handler import contact_handler
from utils.texts import CONTACT_RECEIVED

router = Router()


# ========== Постоянная клавиатура ==========

@router.message(F.text == "📋 Меню")
async def show_menu(message: Message):
    """Показать меню компании"""
    await message.answer(
        MENU_TEXT,
        reply_markup=get_menu_keyboard()
    )


# ========== Callback handlers ==========

@router.callback_query(F.data == "menu:orders")
async def show_my_orders(callback: CallbackQuery, state: FSMContext):
    """Показать заказы пользователя (корзина)"""
    await callback.answer()

    # Перенаправляем на просмотр корзины
    
    await view_order(callback, state)


@router.callback_query(F.data == "phone:use_saved")
async def use_saved_phone_global(callback: CallbackQuery, state: FSMContext):
    """Использовать сохраненный номер телефона (глобальный обработчик)"""
    await callback.answer()

    data = await state.get_data()
    saved_phone = data.get("user_phone")

    # Сохраняем как текущий номер для заказа
    await state.update_data(phone_number=saved_phone)

    # Показываем подтверждение
    await callback.message.edit_text(
        CONTACT_RECEIVED,
        reply_markup=get_back_to_main_keyboard()
    )

    await state.set_state(UserStates.MAIN_MENU)


@router.callback_query(F.data == "phone:enter_new")
async def enter_new_phone_global(callback: CallbackQuery, state: FSMContext):
    """Ввести новый номер телефона (глобальный обработчик)"""
    await callback.answer()

    from keyboards.hotels import get_share_contact_keyboard
    await callback.message.edit_text(
        "Для оформления заказа поделитесь своими контактными данными.\n\nНаш менеджер свяжется с вами для подтверждения.",
        reply_markup=get_share_contact_keyboard()
    )
    # Состояние остается SHARE_CONTACT


@router.callback_query(F.data == "back:main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await callback.answer()

    # Получаем имя пользователя из состояния
    data = await state.get_data()
    user_name = data.get("user_name", "Друг")

    try:
        await callback.message.edit_text(
            get_main_menu_text(user_name),
            reply_markup=get_main_menu_keyboard()
        )
    except TelegramBadRequest:
        # Message may be a media (photo) without text — delete and send new message
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer(
            get_main_menu_text(user_name),
            reply_markup=get_main_menu_keyboard()
        )

    await state.set_state(UserStates.MAIN_MENU)


# ========== Заглушки для основных разделов ==========

@router.callback_query(F.data == "main:other")
async def select_other(callback: CallbackQuery):
    """Другое (заглушка)"""
    await callback.answer("➕ Раздел 'Другое' будет реализован в следующей итерации", show_alert=True)


async def show_main_menu(message: Message, state: FSMContext, edit: bool = False):
    """Вспомогательная функция для показа главного меню"""
    data = await state.get_data()
    user_name = data.get("user_name", "Друг")

    text = get_main_menu_text(user_name)
    keyboard = get_main_menu_keyboard()

    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)

    await state.set_state(UserStates.MAIN_MENU)