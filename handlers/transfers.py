"""Обработчики флоу трансферов"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from states.user_states import UserStates
from keyboards import (
    get_islands_keyboard,
    get_share_contact_keyboard,
    get_back_to_main_keyboard,
    get_transfer_navigation_keyboard,
    get_transfer_card_simple_keyboard,
    get_transfer_booking_keyboard
)
from utils.texts import (
    get_transfers_intro_text,
    get_transfer_card_text,
    get_transfer_booking_text
)
from utils.data_loader import get_data_loader
from utils.contact_handler import contact_handler
from utils.order_manager import order_manager
from utils.helpers import send_items_page
from utils.media_manager import get_transfer_photo

router = Router()


# ========== Старт флоу трансферов ==========

@router.callback_query(F.data == "main:transfers")
async def start_transfers_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу трансферов"""
    await callback.answer()

    data = await state.get_data()
    user_name = data.get("user_name", "Друг")

    await callback.message.edit_text(
        get_transfers_intro_text(user_name),
        reply_markup=get_islands_keyboard()
    )

    await state.set_state(UserStates.TRANSFERS_SELECT_ISLAND)


# ========== Выбор острова ==========

@router.callback_query(UserStates.TRANSFERS_SELECT_ISLAND, F.data.startswith("island:"))
async def select_transfer_island(callback: CallbackQuery, state: FSMContext):
    """Выбор острова для трансфера"""
    await callback.answer()

    island = callback.data.split(":")[1]

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.edit_text("⏳ Загружаю трансферы...")

    # Получаем трансферы для этого острова
    transfers = await get_data_loader().get_transfers_by_island(island)

    if not transfers:
        await loading_msg.edit_text(
            "😔 К сожалению, для выбранного направления трансферы пока недоступны.\n\nПопробуйте другой остров или свяжитесь с нашими менеджерами.",
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Сохраняем данные
    await state.update_data(
        transfers=transfers,
        current_transfer_index=0,
        selected_island=island
    )

    # Показываем первый трансфер с запросом количества людей
    await loading_msg.edit_text(
        "Введите количество человек, включая детей после 2х лет:",
        reply_markup=get_back_to_main_keyboard()
    )

    await state.set_state(UserStates.TRANSFERS_INPUT_PEOPLE)


# ========== Ввод количества людей ==========

@router.message(UserStates.TRANSFERS_INPUT_PEOPLE, F.text)
async def input_people_count(message: Message, state: FSMContext):
    """Обработка ввода количества людей"""
    try:
        people_count = int(message.text.strip())

        if people_count < 1 or people_count > 50:
            await message.answer(
                "❌ Пожалуйста, введите корректное количество человек (от 1 до 50):",
                reply_markup=get_back_to_main_keyboard()
            )
            return

        # Сохраняем количество людей
        await state.update_data(people_count=people_count)

        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass

        # Показываем список трансферов
        await show_transfer_card(message, state, 0)

        await state.set_state(UserStates.TRANSFERS_SHOW_RESULTS)

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите число:",
            reply_markup=get_back_to_main_keyboard()
        )


# ========== Показ карточки трансфера ==========

async def show_transfer_card(message: Message, state: FSMContext, index: int):
    """Показать карточку трансфера"""
    data = await state.get_data()
    transfers = data.get("transfers", [])
    people_count = data.get("people_count", 1)

    if not transfers or index >= len(transfers):
        return

    transfer = transfers[index]
    card_text = get_transfer_card_text(transfer, people_count)

    # Используем новую клавиатуру с кнопкой "Показать все"
    keyboard = get_transfer_navigation_keyboard(
        current_index=index,
        total=len(transfers),
        transfer_id=transfer['id']
    )

    # Пытаемся получить фото
    photo = await get_transfer_photo(transfer['id'])

    if photo:
        await message.answer_photo(
            photo=photo,
            caption=card_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            card_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


async def send_transfers_cards_page(message: Message, state: FSMContext, page: int):
    """Отправить страницу с трансферами блоками (по 5 штук)"""
    data = await state.get_data()
    transfers = data.get("transfers", [])
    people_count = data.get("people_count", 1)

    if not transfers:
        return

    # Функция форматирования карточки
    def format_card(transfer):
        return get_transfer_card_text(transfer, people_count)

    # Функция создания клавиатуры
    def get_keyboard(transfer):
        return get_transfer_card_simple_keyboard(transfer["id"])

    # Функция получения фото
    async def get_photo(transfer):
        return await get_transfer_photo(transfer["id"])

    # Используем универсальную функцию
    await send_items_page(
        message=message,
        items=transfers,
        page=page,
        per_page=5,
        format_card_func=format_card,
        get_keyboard_func=get_keyboard,
        get_photo_func=get_photo,
        callback_prefix="transfer_cards_page",
        page_title="Страница",
        parse_mode="HTML",
        page_1_based=True
    )


# ========== Навигация ==========

@router.callback_query(F.data.startswith("transfer_nav:"))
async def navigate_transfers(callback: CallbackQuery, state: FSMContext):
    """Навигация по трансферам"""
    await callback.answer()

    parts = callback.data.split(":")
    direction = parts[1]
    current_index = int(parts[2])

    new_index = current_index - 1 if direction == "prev" else current_index + 1

    await state.update_data(current_transfer_index=new_index)

    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем новый трансфер
    await show_transfer_card(callback.message, state, new_index)


# ========== Бронирование ==========

@router.callback_query(F.data.startswith("transfer_book:"))
async def book_transfer(callback: CallbackQuery, state: FSMContext):
    """Бронирование трансфера - показываем две кнопки"""
    await callback.answer()

    transfer_id = callback.data.split(":")[1]
    transfer = await get_data_loader().get_transfer_by_id(transfer_id)

    if not transfer:
        return

    data = await state.get_data()
    people_count = data.get("people_count", 1)

    await state.update_data(selected_transfer_id=transfer_id)

    await callback.message.answer(
        get_transfer_booking_text(transfer["name"], people_count),
        reply_markup=get_transfer_booking_keyboard()
    )


@router.callback_query(F.data == "transfer:add_to_order")
async def add_transfer_to_order(callback: CallbackQuery, state: FSMContext):
    """Добавить трансфер в заказ"""
    await callback.answer("Добавлено в заказ! 🛒")

    data = await state.get_data()
    transfer_id = data.get("selected_transfer_id")
    people_count = data.get("people_count", 1)
    transfer = await get_data_loader().get_transfer_by_id(transfer_id)

    if not transfer:
        return

    updated_data = order_manager.add_transfer(data, transfer, people_count)
    await state.update_data(order=updated_data["order"])

    from handlers.main_menu import show_main_menu
    await show_main_menu(callback.message, state)


@router.callback_query(F.data == "transfer:book_now")
async def book_transfer_now(callback: CallbackQuery, state: FSMContext):
    """Забронировать трансфер сейчас - запрос контакта"""
    await callback.answer()

    data = await state.get_data()
    transfer_id = data.get("selected_transfer_id")
    transfer = await get_data_loader().get_transfer_by_id(transfer_id)

    if not transfer:
        return

    # Используем новую функцию для проверки сохраненного номера
    await contact_handler.request_phone(
        callback.message,
        state,
        "Для бронирования трансфера поделитесь своими контактными данными.\n\nНаш менеджер свяжется с вами для подтверждения."
    )

    await state.set_state(UserStates.SHARE_CONTACT)


# ========== Обработка контактов ==========

@router.message(UserStates.SHARE_CONTACT, F.text)
async def process_transfer_phone(message: Message, state: FSMContext):
    """Обработка номера телефона для трансферов"""
    success = await contact_handler.process_text_phone(message, state)
    if success:
        data = await state.get_data()
        updated_data = order_manager.clear_order(data)
        await state.update_data(order=updated_data["order"])


@router.message(UserStates.SHARE_CONTACT, F.contact)
async def process_transfer_contact(message: Message, state: FSMContext):
    """Обработка контакта для трансферов"""
    success = await contact_handler.process_contact(message, state)
    if success:
        data = await state.get_data()
        updated_data = order_manager.clear_order(data)
        await state.update_data(order=updated_data["order"])


# ========== Показ всех трансферов страницами ==========

@router.callback_query(UserStates.TRANSFERS_SHOW_RESULTS, F.data == "transfers:show_all")
async def show_all_transfers_as_cards(callback: CallbackQuery, state: FSMContext):
    """Показать все трансферы отдельными блоками (по 5 штук на странице)"""
    await callback.answer()

    data = await state.get_data()
    transfers = data.get("transfers", [])

    if not transfers:
        await callback.answer("Трансферы не найдены", show_alert=True)
        return

    # Удаляем текущее сообщение с пагинацией
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем первую страницу
    await send_transfers_cards_page(callback.message, state, page=1)


@router.callback_query(UserStates.TRANSFERS_SHOW_RESULTS, F.data.startswith("transfer_cards_page:"))
async def navigate_transfer_cards_pages(callback: CallbackQuery, state: FSMContext):
    """Переключение страниц массовых блоков трансферов"""
    await callback.answer()

    # Получаем номер страницы
    page = int(callback.data.split(":")[1])

    # Удаляем контрольное сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем новую страницу
    await send_transfers_cards_page(callback.message, state, page)
