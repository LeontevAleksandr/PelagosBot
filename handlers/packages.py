"""Обработчики флоу пакетных туров"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

from states.user_states import UserStates
from keyboards import get_back_to_main_keyboard
from utils.texts import (
    get_package_card_text,
    get_package_summary_text
)
from utils.helpers import get_calendar_keyboard, format_date, send_items_page
from utils.data_loader import get_data_loader
from utils.media_manager import media_manager
from utils.contact_handler import contact_handler
from utils.order_manager import order_manager

router = Router()


# ========== Старт флоу пакетных туров ==========

@router.callback_query(F.data == "main:packages")
async def start_packages_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу пакетных туров — загрузка и показ карточек"""
    await callback.answer()

    # Показываем загрузку
    await callback.message.edit_text("⏳ Загружаю пакетные туры...")

    # Получаем все пакетные туры из API
    packages = await get_data_loader().get_all_packages()

    if not packages:
        await callback.message.edit_text(
            "😔 К сожалению, пакетных туров сейчас нет.\n\nПопробуйте позже или свяжитесь с нашими менеджерами.",
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Сохраняем данные
    await state.update_data(
        packages=packages,
        current_package_index=0
    )

    # Удаляем сообщение загрузки
    try:
        await callback.message.delete()
    except:
        pass

    await state.set_state(UserStates.PACKAGE_TOURS_BROWSE)

    # Показываем первый тур
    await show_package_card(callback.message, state, 0)


# ========== Показ карточки тура ==========

async def show_package_card(message: Message, state: FSMContext, index: int):
    """Показать карточку пакетного тура с ленивой загрузкой цен"""
    data = await state.get_data()
    packages = data.get("packages", [])

    if not packages or index >= len(packages):
        return

    package = packages[index]

    # Ленивая загрузка цен
    if not package.get('prices_loaded'):
        loaded = await get_data_loader().get_package_with_prices(package['id'])
        if loaded:
            package = loaded
            packages[index] = package
            await state.update_data(packages=packages)

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

    # Кнопка "Смотреть тур" на сайте
    if package.get("inhttp"):
        buttons.append([InlineKeyboardButton(text="🔍 Смотреть тур", url=package["inhttp"])])

    # Кнопка показать все страницей
    if len(packages) > 1:
        buttons.append([InlineKeyboardButton(text="📋 Показать все страницей", callback_data="pkg:show_all")])
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


async def send_packages_cards_page(message: Message, state: FSMContext, page: int):
    """Отправить страницу с пакетными турами (по 5 штук)"""
    data = await state.get_data()
    packages = data.get("packages", [])

    if not packages:
        return

    # Подгружаем цены для пакетов на текущей странице
    per_page = 5
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(packages))

    for i in range(start_idx, end_idx):
        if not packages[i].get('prices_loaded'):
            loaded = await get_data_loader().get_package_with_prices(packages[i]['id'])
            if loaded:
                packages[i] = loaded

    await state.update_data(packages=packages)

    # Функция форматирования карточки
    def format_card(package):
        return get_package_card_text(package)

    # Функция создания клавиатуры
    def get_keyboard(package):
        btns = [
            [InlineKeyboardButton(text="✅ Забронировать", callback_data=f"pkg_book:{package['id']}")],
        ]
        if package.get("inhttp"):
            btns.append([InlineKeyboardButton(text="🔍 Смотреть тур", url=package["inhttp"])])
        return InlineKeyboardMarkup(inline_keyboard=btns)

    # Функция получения фото
    async def get_photo(package):
        photo_path = package.get("photo")
        return await media_manager.get_photo(photo_path) if photo_path else None

    # Используем универсальную функцию
    await send_items_page(
        message=message,
        items=packages,
        page=page,
        per_page=5,
        format_card_func=format_card,
        get_keyboard_func=get_keyboard,
        get_photo_func=get_photo,
        callback_prefix="pkg_cards_page",
        page_title="Страница"
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


@router.callback_query(F.data == "pkg:show_all")
async def show_all_packages(callback: CallbackQuery, state: FSMContext):
    """Показать все пакетные туры страницей"""
    await callback.answer()

    # Удаляем предыдущее сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем первую страницу
    await send_packages_cards_page(callback.message, state, 0)


@router.callback_query(F.data.startswith("pkg_cards_page:"))
async def navigate_packages_pages(callback: CallbackQuery, state: FSMContext):
    """Навигация по страницам пакетных туров"""
    await callback.answer()

    page = int(callback.data.split(":")[1])

    # Удаляем предыдущие сообщения
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем новую страницу
    await send_packages_cards_page(callback.message, state, page)


# ========== Бронирование: выбор даты ==========

@router.callback_query(F.data.startswith("pkg_book:"))
async def book_package(callback: CallbackQuery, state: FSMContext):
    """Бронирование пакетного тура — показываем календарь для выбора даты"""
    await callback.answer()

    package_id = callback.data.split(":")[1]

    # Загружаем тур с ценами
    package = await get_data_loader().get_package_with_prices(package_id)
    if not package:
        return

    await state.update_data(selected_package_id=package_id)

    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month, back_callback="pkg:back_from_calendar")

    await callback.message.answer(
        f"Вы выбрали тур \"<b>{package['name']}</b>\"\n\nВыберите дату поездки:",
        reply_markup=calendar
    )

    await state.set_state(UserStates.PACKAGE_TOURS_SELECT_DATE)


@router.callback_query(UserStates.PACKAGE_TOURS_SELECT_DATE, F.data == "pkg:back_from_calendar")
async def back_from_packages_calendar(callback: CallbackQuery, state: FSMContext):
    """Возврат к просмотру туров из календаря"""
    await callback.answer()

    # Удаляем сообщение с календарём
    try:
        await callback.message.delete()
    except:
        pass

    # Возвращаемся к просмотру туров
    data = await state.get_data()
    index = data.get("current_package_index", 0)
    await state.set_state(UserStates.PACKAGE_TOURS_BROWSE)
    await show_package_card(callback.message, state, index)


@router.callback_query(UserStates.PACKAGE_TOURS_SELECT_DATE, F.data.startswith("cal:"))
async def navigate_packages_calendar(callback: CallbackQuery):
    """Навигация по календарю"""
    await callback.answer()

    date_str = callback.data.split(":")[1]

    if date_str == "ignore":
        return

    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month, back_callback="pkg:back_from_calendar")

    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.PACKAGE_TOURS_SELECT_DATE, F.data.startswith("date:"))
async def select_package_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты — показать кнопки количества людей"""
    await callback.answer()

    date = callback.data.split(":")[1]
    await state.update_data(desired_travel_date=date)

    # Показываем кнопки выбора количества человек
    buttons = [
        [
            InlineKeyboardButton(text="1 человек", callback_data="pkg_people:1"),
            InlineKeyboardButton(text="2 человека", callback_data="pkg_people:2"),
            InlineKeyboardButton(text="3 человека", callback_data="pkg_people:3")
        ],
        [
            InlineKeyboardButton(text="4 человека", callback_data="pkg_people:4"),
            InlineKeyboardButton(text="5 и более", callback_data="pkg_people:5")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="pkg:back_from_people")]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        f"📅 Дата: <b>{format_date(date)}</b>\n\nВыберите количество человек:",
        reply_markup=keyboard
    )

    await state.set_state(UserStates.PACKAGE_TOURS_SELECT_PEOPLE)


# ========== Бронирование: выбор количества людей ==========

@router.callback_query(UserStates.PACKAGE_TOURS_SELECT_PEOPLE, F.data == "pkg:back_from_people")
async def back_from_people_select(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору даты"""
    await callback.answer()

    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month, back_callback="pkg:back_from_calendar")

    data = await state.get_data()
    package_id = data.get("selected_package_id")
    package = await get_data_loader().get_package_with_prices(package_id)
    package_name = package['name'] if package else "Тур"

    await callback.message.edit_text(
        f"Вы выбрали тур \"<b>{package_name}</b>\"\n\nВыберите дату поездки:",
        reply_markup=calendar
    )

    await state.set_state(UserStates.PACKAGE_TOURS_SELECT_DATE)


@router.callback_query(UserStates.PACKAGE_TOURS_SELECT_PEOPLE, F.data.startswith("pkg_people:"))
async def select_package_people(callback: CallbackQuery, state: FSMContext):
    """Выбор количества людей — показать итоговую стоимость"""
    await callback.answer()

    people_count = int(callback.data.split(":")[1])

    data = await state.get_data()
    package_id = data.get("selected_package_id")
    desired_date = data.get("desired_travel_date", "")

    # Загружаем тур с ценами
    package = await get_data_loader().get_package_with_prices(package_id)
    if not package:
        return

    # Получаем цену для выбранного количества людей
    price_per_person = get_data_loader().get_price_for_people_count(package, people_count)

    await state.update_data(
        package_people_count=people_count,
        package_price_per_person=price_per_person
    )

    # Формируем итоговый текст
    date_str = format_date(desired_date) if desired_date else "по согласованию"
    summary_text = get_package_summary_text(package['name'], date_str, people_count, price_per_person)

    buttons = [
        [InlineKeyboardButton(text="🛒 Добавить в заказ", callback_data="pkg:add_to_order")],
        [InlineKeyboardButton(text="✅ Забронировать сейчас", callback_data="pkg:book_now")],
        [InlineKeyboardButton(text="⬅️ Назад к турам", callback_data="pkg:back_to_browse")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(
        summary_text,
        reply_markup=keyboard
    )


# ========== Подтверждение бронирования ==========

@router.callback_query(F.data == "pkg:back_to_browse")
async def back_to_browse(callback: CallbackQuery, state: FSMContext):
    """Возврат к просмотру туров"""
    await callback.answer()

    try:
        await callback.message.delete()
    except:
        pass

    data = await state.get_data()
    index = data.get("current_package_index", 0)
    await state.set_state(UserStates.PACKAGE_TOURS_BROWSE)
    await show_package_card(callback.message, state, index)


@router.callback_query(F.data == "pkg:add_to_order")
async def add_package_to_order(callback: CallbackQuery, state: FSMContext):
    """Добавить пакетный тур в заказ"""
    await callback.answer("Добавлено в заказ! 🛒")

    data = await state.get_data()
    package_id = data.get("selected_package_id")
    package = await get_data_loader().get_package_with_prices(package_id)

    if not package:
        return

    desired_date = data.get("desired_travel_date", "")
    people_count = data.get("package_people_count", 1)
    price_per_person = data.get("package_price_per_person", 0)

    updated_data = order_manager.add_package(
        data, package, desired_date,
        people_count=people_count,
        price_per_person=price_per_person
    )
    await state.update_data(order=updated_data["order"])

    from handlers.main_menu import show_main_menu
    await show_main_menu(callback.message, state)


@router.callback_query(F.data == "pkg:book_now")
async def book_package_now(callback: CallbackQuery, state: FSMContext):
    """Забронировать пакетный тур сейчас — запрос контакта"""
    await callback.answer()

    data = await state.get_data()
    package_id = data.get("selected_package_id")
    package = await get_data_loader().get_package_with_prices(package_id)

    if not package:
        return

    desired_date = data.get("desired_travel_date", "")
    people_count = data.get("package_people_count", 1)
    price_per_person = data.get("package_price_per_person", 0)

    updated_data = order_manager.add_package(
        data, package, desired_date,
        people_count=people_count,
        price_per_person=price_per_person
    )
    await state.update_data(order=updated_data["order"])

    # Запрашиваем контакт
    await contact_handler.request_phone(
        callback.message,
        state,
        "Для бронирования пакетного тура поделитесь своими контактными данными.\n\nНаш менеджер свяжется с вами для подтверждения."
    )

    await state.set_state(UserStates.SHARE_CONTACT)


# ========== Обработка контактов ==========

@router.message(UserStates.SHARE_CONTACT, F.text)
async def process_package_phone(message: Message, state: FSMContext):
    """Обработка номера телефона для пакетных туров"""
    if await contact_handler.process_text_phone(message, state):
        from handlers.order import finalize_order
        await finalize_order(message, state)


@router.message(UserStates.SHARE_CONTACT, F.contact)
async def process_package_contact(message: Message, state: FSMContext):
    """Обработка контакта для пакетных туров"""
    if await contact_handler.process_contact(message, state):
        from handlers.order import finalize_order
        await finalize_order(message, state)
