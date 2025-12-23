"""Обработчики управления профилем пользователя"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from states.user_states import UserStates
from keyboards import get_back_to_main_keyboard
from utils.helpers import validate_phone_number

router = Router()


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура профиля пользователя"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="profile:edit_name")],
        [InlineKeyboardButton(text="📱 Изменить телефон", callback_data="profile:edit_phone")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


@router.callback_query(F.data == "menu:profile")
async def show_profile(callback: CallbackQuery, state: FSMContext):
    """Показать профиль пользователя"""
    await callback.answer()

    data = await state.get_data()
    user_name = data.get("user_name", "Не указано")
    user_phone = data.get("user_phone", "Не указан")

    profile_text = (
        f"👤 Ваш профиль\n\n"
        f"Имя: {user_name}\n"
        f"Телефон: {user_phone}\n\n"
        f"Эти данные будут использоваться при оформлении заказов."
    )

    await callback.message.edit_text(
        profile_text,
        reply_markup=get_profile_keyboard()
    )

    await state.set_state(UserStates.PROFILE_VIEW)


@router.callback_query(F.data == "profile:edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование имени"""
    await callback.answer()

    await callback.message.edit_text(
        "✏️ Введите новое имя:",
        reply_markup=get_back_to_main_keyboard()
    )

    await state.set_state(UserStates.PROFILE_EDIT_NAME)


@router.message(UserStates.PROFILE_EDIT_NAME, F.text)
async def process_new_name(message: Message, state: FSMContext):
    """Обработка нового имени"""
    new_name = message.text.strip()

    if len(new_name) < 2:
        await message.answer(
            "❌ Имя слишком короткое. Пожалуйста, введите корректное имя (минимум 2 символа).",
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Сохраняем новое имя
    await state.update_data(user_name=new_name)

    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    # Показываем обновленный профиль
    data = await state.get_data()
    user_phone = data.get("user_phone", "Не указан")

    profile_text = (
        f"✅ Имя успешно изменено!\n\n"
        f"👤 Ваш профиль\n\n"
        f"Имя: {new_name}\n"
        f"Телефон: {user_phone}\n\n"
        f"Эти данные будут использоваться при оформлении заказов."
    )

    await message.answer(
        profile_text,
        reply_markup=get_profile_keyboard()
    )

    await state.set_state(UserStates.PROFILE_VIEW)


@router.callback_query(F.data == "profile:edit_phone")
async def edit_phone(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование телефона"""
    await callback.answer()

    from keyboards.hotels import get_share_contact_keyboard

    await callback.message.edit_text(
        "📱 Введите новый номер телефона или поделитесь контактом.\n\n"
        "Формат: +79991234567 или 89991234567",
        reply_markup=get_share_contact_keyboard()
    )

    await state.set_state(UserStates.PROFILE_EDIT_PHONE)


@router.message(UserStates.PROFILE_EDIT_PHONE, F.text)
async def process_new_phone(message: Message, state: FSMContext):
    """Обработка нового номера телефона"""
    valid, phone_number = validate_phone_number(message.text)

    if not valid:
        await message.answer(
            "❌ Неверный формат номера телефона.\n\n"
            "Пожалуйста, введите номер в формате:\n"
            "+79991234567 или 89991234567",
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Сохраняем новый номер
    await state.update_data(user_phone=phone_number)

    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    # Показываем обновленный профиль
    data = await state.get_data()
    user_name = data.get("user_name", "Не указано")

    profile_text = (
        f"✅ Номер телефона успешно изменен!\n\n"
        f"👤 Ваш профиль\n\n"
        f"Имя: {user_name}\n"
        f"Телефон: {phone_number}\n\n"
        f"Эти данные будут использоваться при оформлении заказов."
    )

    await message.answer(
        profile_text,
        reply_markup=get_profile_keyboard()
    )

    await state.set_state(UserStates.PROFILE_VIEW)


@router.message(UserStates.PROFILE_EDIT_PHONE, F.contact)
async def process_new_contact(message: Message, state: FSMContext):
    """Обработка нового контакта через кнопку Telegram"""
    phone_number = message.contact.phone_number

    # Добавляем + если его нет
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    # Сохраняем новый номер
    await state.update_data(user_phone=phone_number)

    # Показываем обновленный профиль
    data = await state.get_data()
    user_name = data.get("user_name", "Не указано")

    profile_text = (
        f"✅ Номер телефона успешно изменен!\n\n"
        f"👤 Ваш профиль\n\n"
        f"Имя: {user_name}\n"
        f"Телефон: {phone_number}\n\n"
        f"Эти данные будут использоваться при оформлении заказов."
    )

    await message.answer(
        profile_text,
        reply_markup=get_profile_keyboard()
    )

    await state.set_state(UserStates.PROFILE_VIEW)
