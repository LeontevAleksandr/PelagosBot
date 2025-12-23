"""Обработчики для управления заказом/корзиной"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from states.user_states import UserStates
from keyboards import get_share_contact_keyboard, get_back_to_main_keyboard
from utils.order_manager import order_manager
from utils.contact_handler import contact_handler

router = Router()


@router.callback_query(F.data == "order:view")
async def view_order(callback: CallbackQuery, state: FSMContext):
    """Просмотр корзины"""
    await callback.answer()

    data = await state.get_data()
    order = order_manager.get_order(data)

    if not order:
        await callback.message.edit_text(
            "🛒 Ваша корзина пуста\n\nДобавьте услуги из меню, чтобы оформить заказ.",
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Формируем клавиатуру с управлением
    buttons = []

    # Кнопки удаления для каждого элемента
    for i in range(len(order)):
        buttons.append([InlineKeyboardButton(
            text=f"❌ Удалить {i + 1}",
            callback_data=f"order:remove:{i}"
        )])

    # Кнопки управления
    buttons.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="order:clear")])
    buttons.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="order:checkout")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        order_manager.format_order(order),
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("order:remove:"))
async def remove_from_order(callback: CallbackQuery, state: FSMContext):
    """Удалить элемент из корзины"""
    await callback.answer("Удалено")

    index = int(callback.data.split(":")[2])

    data = await state.get_data()
    updated_data = order_manager.remove_item(data, index)
    await state.update_data(order=updated_data["order"])

    # Обновляем отображение
    await view_order(callback, state)


@router.callback_query(F.data == "order:clear")
async def clear_order(callback: CallbackQuery, state: FSMContext):
    """Очистить корзину"""
    await callback.answer("Корзина очищена")

    data = await state.get_data()
    updated_data = order_manager.clear_order(data)
    await state.update_data(order=updated_data["order"])

    await callback.message.edit_text(
        "🛒 Корзина очищена",
        reply_markup=get_back_to_main_keyboard()
    )


@router.callback_query(F.data == "order:checkout")
async def checkout_order(callback: CallbackQuery, state: FSMContext):
    """Оформить заказ - запросить контакт"""
    await callback.answer()

    data = await state.get_data()
    order = order_manager.get_order(data)

    if not order:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    # Используем новую функцию для проверки сохраненного номера
    await contact_handler.request_phone(
        callback.message,
        state,
        "Для оформления заказа поделитесь своими контактными данными.\n\nНаш менеджер свяжется с вами для подтверждения."
    )

    await state.set_state(UserStates.SHARE_CONTACT)


# Обработка контактов при оформлении заказа
@router.message(UserStates.SHARE_CONTACT, F.text)
async def process_order_phone(message: Message, state: FSMContext):
    """Обработка номера телефона при оформлении заказа"""
    # После успешной обработки контакта очищаем корзину
    success = await contact_handler.process_text_phone(message, state)
    if success:
        data = await state.get_data()
        updated_data = order_manager.clear_order(data)
        await state.update_data(order=updated_data["order"])


@router.message(UserStates.SHARE_CONTACT, F.contact)
async def process_order_contact(message: Message, state: FSMContext):
    """Обработка контакта при оформлении заказа"""
    # После успешной обработки контакта очищаем корзину
    success = await contact_handler.process_contact(message, state)
    if success:
        data = await state.get_data()
        updated_data = order_manager.clear_order(data)
        await state.update_data(order=updated_data["order"])
