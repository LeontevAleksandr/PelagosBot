"""Обработчики для управления заказом/корзиной"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from states.user_states import UserStates
from keyboards import get_share_contact_keyboard, get_back_to_main_keyboard
from utils.order_manager import order_manager
from utils.contact_handler import contact_handler
from utils.frontend_connector import frontend_connector

logger = logging.getLogger(__name__)

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
    # После успешной обработки контакта отправляем заказ в API и очищаем корзину
    success = await contact_handler.process_text_phone(message, state)
    if success:
        await finalize_order(message, state)


@router.message(UserStates.SHARE_CONTACT, F.contact)
async def process_order_contact(message: Message, state: FSMContext):
    """Обработка контакта при оформлении заказа"""
    # После успешной обработки контакта отправляем заказ в API и очищаем корзину
    success = await contact_handler.process_contact(message, state)
    if success:
        await finalize_order(message, state)


async def finalize_order(message: Message, state: FSMContext):
    """
    Финализация заказа: отправка в API Pelagos и очистка корзины

    Args:
        message: Сообщение от пользователя
        state: Состояние FSM
    """
    data = await state.get_data()
    order = order_manager.get_order(data)

    if not order:
        logger.warning("Попытка финализировать пустой заказ")
        return

    # Отправляем заказ в Pelagos API
    logger.info(f"🚀 Отправка заказа в Pelagos API для пользователя {data.get('user_name')}")

    try:
        result = await frontend_connector.create_order_from_cart(
            state_data=data,
            order_items=order
        )

        if result and result.get("success"):
            order_id = result.get("order_id")
            parts_added = result.get("parts_added", 0)
            parts_failed = result.get("parts_failed", 0)

            logger.info(f"✅ Заказ #{order_id} успешно создан в Pelagos")

            # Формируем сообщение для пользователя
            success_msg = f"✅ <b>Заказ успешно оформлен!</b>\n\n"
            success_msg += f"Номер заказа: <b>#{order_id}</b>\n"
            success_msg += f"Добавлено позиций: {parts_added}\n\n"

            if parts_failed > 0:
                success_msg += f"⚠️ Некоторые позиции ({parts_failed}) не удалось добавить.\n\n"

            success_msg += "Наш менеджер свяжется с вами в ближайшее время для подтверждения деталей заказа."

            await message.answer(success_msg, reply_markup=get_back_to_main_keyboard())

        else:
            error_msg = result.get("message", "Неизвестная ошибка") if result else "Не удалось создать заказ"
            logger.error(f"❌ Ошибка создания заказа в Pelagos: {error_msg}")

            await message.answer(
                f"⚠️ <b>Заказ принят, но возникла проблема с отправкой в систему</b>\n\n"
                f"Ваши данные сохранены, менеджер свяжется с вами для уточнения деталей.\n\n"
                f"Технические детали: {error_msg}",
                reply_markup=get_back_to_main_keyboard()
            )

    except Exception as e:
        logger.error(f"❌ Критическая ошибка при финализации заказа: {e}", exc_info=True)

        await message.answer(
            "⚠️ <b>Заказ принят</b>\n\n"
            "Возникла техническая проблема, но ваши данные сохранены. "
            "Менеджер свяжется с вами в ближайшее время.",
            reply_markup=get_back_to_main_keyboard()
        )

    finally:
        # Очищаем корзину в любом случае
        updated_data = order_manager.clear_order(data)
        await state.update_data(order=updated_data["order"])
