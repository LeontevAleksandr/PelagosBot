"""Обработчики главного меню"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

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
async def show_my_orders(callback: CallbackQuery):
    """Показать заказы пользователя"""
    await callback.answer()
    
    user_id = callback.from_user.id
    orders = await get_orders_for_user(user_id)
    
    if not orders:
        text = MY_ORDERS_EMPTY
    else:
        text = MY_ORDERS_TEXT
        # TODO: Добавить форматирование списка заказов
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_main_keyboard()
    )


@router.callback_query(F.data == "back:main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    await callback.answer()
    
    # Получаем имя пользователя из состояния
    data = await state.get_data()
    user_name = data.get("user_name", "Друг")
    
    await callback.message.edit_text(
        get_main_menu_text(user_name),
        reply_markup=get_main_menu_keyboard()
    )
    
    await state.set_state(UserStates.MAIN_MENU)


# ========== Заглушки для основных разделов ==========

# Отели реализованы в handlers/hotels.py

@router.callback_query(F.data == "main:excursions")
async def select_excursions(callback: CallbackQuery):
    """Выбор экскурсий (заглушка)"""
    await callback.answer("🏝 Раздел 'Экскурсии' будет реализован в следующей итерации", show_alert=True)


@router.callback_query(F.data == "main:packages")
async def select_packages(callback: CallbackQuery):
    """Выбор пакетных туров (заглушка)"""
    await callback.answer("📦 Раздел 'Пакетные туры' будет реализован в следующей итерации", show_alert=True)


@router.callback_query(F.data == "main:transfers")
async def select_transfers(callback: CallbackQuery):
    """Выбор трансферов (заглушка)"""
    await callback.answer("🚗 Раздел 'Трансферы' будет реализован в следующей итерации", show_alert=True)


@router.callback_query(F.data == "main:other")
async def select_other(callback: CallbackQuery):
    """Другое (заглушка)"""
    await callback.answer("➕ Раздел 'Другое' будет реализован в следующей итерации", show_alert=True)