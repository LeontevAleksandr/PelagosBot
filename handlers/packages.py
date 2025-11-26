"""Обработчики флоу пакетных туров"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

from states.user_states import UserStates
from keyboards import get_share_contact_keyboard, get_back_to_main_keyboard
from utils.texts import (
    get_packages_intro_text,
    get_package_card_text,
    get_package_booking_text
)
from utils.helpers import get_calendar_keyboard, format_date
from utils.data_loader import data_loader
from utils.media_manager import media_manager
from utils.contact_handler import contact_handler

router = Router()


# ========== Старт флоу пакетных туров ==========

@router.callback_query(F.data == "main:packages")
async def start_packages_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу пакетных туров"""
    await callback.answer()

    data = await state.get_data()
    user_name = data.get("user_name", "Друг")

    # Показываем календарь для выбора даты
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month, back_callback="packages:back_from_calendar")

    await callback.message.edit_text(
        get_packages_intro_text(user_name) + "\n\nВыберите желаемую дату начала тура:",
        reply_markup=calendar
    )

    await state.set_state(UserStates.PACKAGE_TOURS_SELECT_DATE)


# ========== Выбор даты ==========

@router.callback_query(UserStates.PACKAGE_TOURS_SELECT_DATE, F.data == "packages:back_from_calendar")
async def back_from_packages_calendar(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню из календаря пакетов"""
    await callback.answer()

    from handlers.main_menu import show_main_menu
    await show_main_menu(callback.message, state, edit=True)


@router.callback_query(UserStates.PACKAGE_TOURS_SELECT_DATE, F.data.startswith("cal:"))
async def navigate_packages_calendar(callback: CallbackQuery):
    """Навигация по календарю"""
    await callback.answer()

    date_str = callback.data.split(":")[1]

    if date_str == "ignore":
        return

    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month, back_callback="packages:back_from_calendar")

    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.PACKAGE_TOURS_SELECT_DATE, F.data.startswith("date:"))
async def select_package_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты и показ туров"""
    await callback.answer()
    
    date = callback.data.split(":")[1]
    
    # Получаем пакетные туры близкие к этой дате
    packages = data_loader.get_packages_by_date(date)
    
    if not packages:
        await callback.message.edit_text(
            f"😔 К сожалению, на выбранные даты ({format_date(date)}) пакетных туров не найдено.\n\nПопробуйте выбрать другую дату или свяжитесь с нашими менеджерами.",
            reply_markup=get_back_to_main_keyboard()
        )
        return
    
    # Сохраняем данные
    await state.update_data(
        packages=packages,
        current_package_index=0,
        selected_date=date
    )
    
    # Удаляем календарь
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем первый тур
    await show_package_card(callback.message, state, 0)


# ========== Показ карточки тура ==========

async def show_package_card(message: Message, state: FSMContext, index: int):
    """Показать карточку пакетного тура"""
    data = await state.get_data()
    packages = data.get("packages", [])
    
    if not packages or index >= len(packages):
        return
    
    package = packages[index]
    card_text = get_package_card_text(package)
    
    # Формируем клавиатуру
    buttons = []
    
    # Кнопка бронирования
    buttons.append([InlineKeyboardButton(text="✅ Забронировать", callback_data=f"pkg_book:{package['id']}")])
    
    # Навигация
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущий", callback_data=f"pkg_nav:prev:{index}"))
    if index < len(packages) - 1:
        nav_buttons.append(InlineKeyboardButton(text="Следующий ➡️", callback_data=f"pkg_nav:next:{index}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Кнопка "Смотреть тур"
    if package.get("url"):
        buttons.append([InlineKeyboardButton(text="🔍 Смотреть тур", url=package["url"])])
    
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Пытаемся получить фото
    photo_path = package.get("photo")
    photo = await media_manager.get_photo(photo_path) if photo_path else None
    
    if photo:
        await message.answer_photo(
            photo=photo,
            caption=card_text,
            reply_markup=keyboard
        )
    else:
        await message.answer(
            card_text,
            reply_markup=keyboard
        )


# ========== Навигация ==========

@router.callback_query(F.data.startswith("pkg_nav:"))
async def navigate_packages(callback: CallbackQuery, state: FSMContext):
    """Навигация по пакетным турам"""
    await callback.answer()
    
    parts = callback.data.split(":")
    direction = parts[1]
    current_index = int(parts[2])
    
    new_index = current_index - 1 if direction == "prev" else current_index + 1
    
    await state.update_data(current_package_index=new_index)
    
    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем новый тур
    await show_package_card(callback.message, state, new_index)


# ========== Бронирование ==========

@router.callback_query(F.data.startswith("pkg_book:"))
async def book_package(callback: CallbackQuery, state: FSMContext):
    """Бронирование пакетного тура"""
    await callback.answer()
    
    package_id = callback.data.split(":")[1]
    package = data_loader.get_package_by_id(package_id)
    
    if not package:
        return
    
    await state.update_data(selected_package_id=package_id)
    
    # Показываем подтверждение и запрос контакта
    date_str = f"{format_date(package['start_date'])} - {format_date(package['end_date'])}"
    
    await callback.message.answer(
        get_package_booking_text(package["name"], date_str),
        reply_markup=get_share_contact_keyboard()
    )
    
    await state.set_state(UserStates.SHARE_CONTACT)


# ========== Обработка контактов ==========

@router.message(UserStates.SHARE_CONTACT, F.text)
async def process_package_phone(message: Message, state: FSMContext):
    """Обработка номера телефона для пакетных туров"""
    await contact_handler.process_text_phone(message, state)


@router.message(UserStates.SHARE_CONTACT, F.contact)
async def process_package_contact(message: Message, state: FSMContext):
    """Обработка контакта для пакетных туров"""
    await contact_handler.process_contact(message, state)