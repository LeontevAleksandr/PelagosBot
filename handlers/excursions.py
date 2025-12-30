"""Обработчики флоу экскурсий"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

from states.user_states import UserStates
from keyboards import (
    get_excursion_type_keyboard,
    get_group_excursion_keyboard,
    get_no_group_excursions_keyboard,
    get_private_excursion_keyboard,
    get_companions_list_keyboard,
    get_companions_excursion_keyboard,
    get_companions_create_agree_keyboard,
    get_companions_select_excursion_keyboard,
    get_share_contact_keyboard,
    get_back_to_main_keyboard,
    get_group_excursion_full_keyboard,
    get_action_choice_keyboard,
    get_group_month_excursion_detail_keyboard,
    get_month_excursions_list_keyboard,
    get_private_islands_keyboard
)
from handlers.main_menu import show_main_menu
from utils.texts import (
    EXCURSIONS_SELECT_TYPE,
    EXCURSIONS_GROUP_INTRO,
    EXCURSIONS_PRIVATE_INTRO,
    COMPANIONS_INTRO,
    COMPANIONS_HOW_IT_WORKS,
    COMPANIONS_SELECT_EXCURSION,
    COMPANIONS_SELECT_DATE,
    COMPANIONS_INPUT_PEOPLE,
    NO_EXCURSIONS_FOUND,
    get_group_excursion_card_text,
    get_private_excursion_card_text,
    get_companions_excursion_card_text,
    get_excursion_join_text,
    get_excursion_booking_text,
    get_companions_created_text,
    CONTACT_RECEIVED
)
from utils.helpers import (
    get_calendar_keyboard,
    format_date,
    send_items_page,
    send_excursion_card_with_photo
)
from utils.data_loader import get_data_loader
from utils.media_manager import get_excursion_photo
from utils.contact_handler import contact_handler
from utils.order_manager import order_manager

router = Router()

EXCURSIONS_PER_PAGE = 5
MAX_EXCURSION_NAME_LENGTH = 40

# Названия месяцев в именительном и родительном падежах
MONTH_NAMES = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

MONTH_NAMES_GENITIVE = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
]


# ========== Вспомогательные функции ==========

def get_people_count_keyboard():
    """Создать клавиатуру для выбора количества людей"""
    buttons = [
        [
            InlineKeyboardButton(text="1 человек", callback_data="people_count:1"),
            InlineKeyboardButton(text="2 человека", callback_data="people_count:2"),
            InlineKeyboardButton(text="3 человека", callback_data="people_count:3")
        ],
        [
            InlineKeyboardButton(text="4 человека", callback_data="people_count:4"),
            InlineKeyboardButton(text="5 и более", callback_data="people_count:5")
        ],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ========== Обработчик выбора количества людей ==========

@router.callback_query(F.data.startswith("people_count:"))
async def handle_people_count_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора количества людей через кнопки"""
    await callback.answer()

    count_str = callback.data.split(":")[1]

    # Сохраняем выбранное количество
    people_count = int(count_str)

    # Получаем текущее состояние для определения контекста
    current_state = await state.get_state()

    # В зависимости от текущего состояния выполняем соответствующую логику
    if current_state == UserStates.EXCURSIONS_GROUP_INPUT_PEOPLE:
        # Для групповых экскурсий - сохраняем количество и показываем список экскурсий
        # Цена фиксированная за человека, но показываем общую стоимость
        await state.update_data(
            excursion_people_count=people_count,
            current_excursion_index=0
        )

        # Показываем сообщение о загрузке
        loading_msg = await callback.message.edit_text("⏳ Подготавливаю экскурсии...")

        # Небольшая задержка для плавности UX
        try:
            await loading_msg.delete()
        except:
            pass

        # Показываем первую экскурсию с учетом количества людей
        await show_group_excursion(callback.message, state, 0)

    elif current_state == UserStates.EXCURSIONS_PRIVATE_INPUT_PEOPLE:
        # Для индивидуальных экскурсий
        data = await state.get_data()
        island = data.get("island")

        loading_msg = await callback.message.edit_text("⏳ Загружаю индивидуальные экскурсии...")

        excursions = await get_data_loader().get_excursions_by_filters(
            island=island,
            excursion_type="private"
        )

        try:
            await loading_msg.delete()
        except:
            pass

        if not excursions:
            await callback.message.answer(
                "😔 К сожалению, индивидуальных экскурсий не найдено.",
                reply_markup=get_back_to_main_keyboard()
            )
            return

        await state.update_data(
            people_count=people_count,
            excursions=excursions,
            current_excursion_index=0
        )

        await show_private_excursion(callback.message, state, 0)
        await state.set_state(UserStates.EXCURSIONS_SHOW_RESULTS)

    elif current_state == UserStates.COMPANIONS_JOIN_INPUT_PEOPLE:
        # Для присоединения к попутчикам
        await state.update_data(excursion_people_count=people_count)

        # Показываем сообщение о загрузке
        loading_msg = await callback.message.edit_text("⏳ Загружаю информацию об экскурсии...")

        data = await state.get_data()
        excursion_id = data.get("selected_excursion_id")
        excursion = await get_data_loader().get_excursion_by_id(excursion_id)

        if not excursion:
            await loading_msg.edit_text("❌ Ошибка: экскурсия не найдена")
            return

        keyboard = get_action_choice_keyboard("companion")
        await loading_msg.edit_text(
            get_excursion_join_text(excursion["name"]),
            reply_markup=keyboard
        )

    elif current_state == UserStates.COMPANIONS_CREATE_INPUT_PEOPLE:
        # Для создания заявки на попутчиков
        await state.update_data(people_count=people_count)

        loading_msg = await callback.message.edit_text("⏳ Загружаю доступные острова с экскурсиями...")

        try:
            islands = await get_data_loader().excursions_loader.get_available_islands_with_count()

            if not islands:
                await loading_msg.edit_text(
                    "😔 К сожалению, не удалось загрузить список островов с экскурсиями. Попробуйте позже.",
                    reply_markup=get_back_to_main_keyboard()
                )
                return

            await loading_msg.edit_text(
                f"**Создание заявки на поиск попутчиков**\n\n"
                f"Выберите остров для поиска экскурсий:\n"
                f"_(Всего найдено {len(islands)} островов с экскурсиями)_",
                reply_markup=get_private_islands_keyboard(islands),
                parse_mode="Markdown"
            )

            await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_ISLAND)

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки островов для создания заявки на попутчиков: {e}")
            await loading_msg.edit_text(
                "😔 Произошла ошибка при загрузке списка островов.",
                reply_markup=get_back_to_main_keyboard()
            )


# ========== Старт флоу экскурсий ==========

@router.callback_query(F.data == "main:excursions")
async def start_excursions_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу экскурсий - выбор типа экскурсии"""
    await callback.answer()

    # Очищаем filtered_excursions и island если они остались от предыдущих сессий
    await state.update_data(filtered_excursions=None, search_query=None, island=None)

    await callback.message.edit_text(
        EXCURSIONS_SELECT_TYPE,
        reply_markup=get_excursion_type_keyboard()
    )

    await state.set_state(UserStates.EXCURSIONS_SELECT_TYPE)



# ========== ВЕТКА A: Групповые экскурсии ==========

@router.callback_query(UserStates.EXCURSIONS_SELECT_TYPE, F.data == "exc_type:group")
async def select_group_excursions(callback: CallbackQuery, state: FSMContext):
    """Выбор групповых экскурсий"""
    await callback.answer()
    
    await callback.message.edit_text(EXCURSIONS_GROUP_INTRO)

    # Показываем календарь
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month, back_callback="excursions:back_from_calendar")

    await callback.message.answer(
        "Выберите дату:",
        reply_markup=calendar
    )

    await state.set_state(UserStates.EXCURSIONS_GROUP_SELECT_DATE)


@router.callback_query(UserStates.EXCURSIONS_GROUP_SELECT_DATE, F.data.startswith("cal:"))
async def navigate_group_calendar(callback: CallbackQuery):
    """Навигация по календарю групповых экскурсий"""
    await callback.answer()

    date_str = callback.data.split(":")[1]

    if date_str == "ignore":
        return

    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month, back_callback="excursions:back_from_calendar")

    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.EXCURSIONS_GROUP_SELECT_DATE, F.data.startswith("date:"))
async def select_group_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для групповых экскурсий"""
    await callback.answer()

    date = callback.data.split(":")[1]

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.edit_text("⏳ Загружаю экскурсии на выбранную дату...")

    # Получаем экскурсии на эту дату
    excursions = await get_data_loader().get_excursions_by_filters(
        island=None,
        excursion_type="group",
        date=date
    )

    if not excursions:
        await loading_msg.edit_text(
            NO_EXCURSIONS_FOUND,
            reply_markup=get_no_group_excursions_keyboard(selected_date=date)
        )
        await state.update_data(current_date=date)
        return

    # Дозагружаем цены для всех экскурсий (фиксированная цена за человека)
    logger.info(f"📊 Дозагрузка цен для {len(excursions)} групповых экскурсий...")
    for excursion in excursions:
        if not excursion.get('price_usd') or excursion.get('price_usd') == 0:
            # Загружаем полные данные экскурсии
            full_excursion = await get_data_loader().get_excursion_by_id(excursion['id'])
            if full_excursion and full_excursion.get('price_usd'):
                logger.info(f"   ✓ {excursion['name']}: ${full_excursion['price_usd']} за чел")
                excursion['price'] = full_excursion['price_usd']
                excursion['price_usd'] = full_excursion['price_usd']

    # Сохраняем экскурсии и дату
    await state.update_data(
        excursions=excursions,
        current_date=date
    )

    # Запрашиваем количество человек
    await loading_msg.edit_text(
        "Сколько вас человек собирается ехать (взрослые и дети старше 7 лет)?",
        reply_markup=get_people_count_keyboard()
    )
    await state.set_state(UserStates.EXCURSIONS_GROUP_INPUT_PEOPLE)


async def show_group_excursion(message: Message, state: FSMContext, index: int, expanded: bool = False):
    """Показать карточку групповой экскурсии"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("excursion_people_count", 1)

    if not excursions or index >= len(excursions):
        return

    excursion = excursions[index]
    card_text = get_group_excursion_card_text(excursion, people_count, expanded)

    # Проверяем наличие других экскурсий на эту же дату (для пагинации)
    has_prev = index > 0
    has_next = index < len(excursions) - 1
    current_date = data.get("current_date")

    # Используем клавиатуру из keyboards
    keyboard = get_group_excursion_full_keyboard(
        excursion_id=excursion['id'],
        index=index,
        has_prev=has_prev,
        has_next=has_next,
        current_date=current_date,
        expanded=expanded
    )

    # Используем универсальную функцию отправки
    await send_excursion_card_with_photo(message, card_text, keyboard, excursion["id"])


async def _update_group_excursion_card(callback: CallbackQuery, state: FSMContext, index: int, expanded: bool):
    """Вспомогательная функция для обновления карточки групповой экскурсии"""
    data = await state.get_data()
    excursions = data.get("excursions", [])

    if not excursions or index >= len(excursions):
        return

    excursion = excursions[index]
    people_count = data.get("excursion_people_count", 1)
    card_text = get_group_excursion_card_text(excursion, people_count, expanded=expanded)

    has_prev = index > 0
    has_next = index < len(excursions) - 1
    current_date = data.get("current_date")

    # Используем клавиатуру из keyboards
    keyboard = get_group_excursion_full_keyboard(
        excursion_id=excursion['id'],
        index=index,
        has_prev=has_prev,
        has_next=has_next,
        current_date=current_date,
        expanded=expanded
    )

    # Удаляем старое сообщение
    await callback.message.delete()

    # Используем универсаль��ую функцию отправки
    await send_excursion_card_with_photo(callback.message, card_text, keyboard, excursion["id"])


@router.callback_query(F.data.startswith("exc_group_expand:"))
async def expand_group_excursion(callback: CallbackQuery, state: FSMContext):
    """Развернуть описание групповой экскурсии"""
    await callback.answer()
    index = int(callback.data.split(":")[1])
    await _update_group_excursion_card(callback, state, index, expanded=True)


@router.callback_query(F.data.startswith("exc_group_collapse:"))
async def collapse_group_excursion(callback: CallbackQuery, state: FSMContext):
    """Свернуть описание групповой экскурсии"""
    await callback.answer()
    index = int(callback.data.split(":")[1])
    await _update_group_excursion_card(callback, state, index, expanded=False)


@router.callback_query(F.data.startswith("exc_group_nav:"))
async def navigate_group_excursions(callback: CallbackQuery, state: FSMContext):
    """Навигация между групповыми экскурсиями на одну дату"""
    await callback.answer()
    
    parts = callback.data.split(":")
    direction = parts[1]
    current_index = int(parts[2])
    
    new_index = current_index - 1 if direction == "prev" else current_index + 1
    
    await state.update_data(current_excursion_index=new_index)

    # Удаляем текущее сообщение
    await callback.message.delete()

    # Показываем новую экскурсию
    await show_group_excursion(callback.message, state, new_index)


async def send_excursions_cards_page(message: Message, state: FSMContext, page: int):
    """Отправ��ть страницу с экскурсиями (по 5 штук)"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("excursion_people_count", 1)

    if not excursions:
        return

    # Функция форматирования карточки
    def format_card(excursion):
        return get_group_excursion_card_text(excursion, people_count, expanded=False)

    # Функция создания клавиатуры
    def get_keyboard(excursion):
        buttons = [
            [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"exc_join:{excursion['id']}")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Функция получения фото
    async def get_photo(excursion):
        return await get_excursion_photo(excursion["id"])

    # Используем универсальную функцию
    await send_items_page(
        message=message,
        items=excursions,
        page=page,
        per_page=EXCURSIONS_PER_PAGE,
        format_card_func=format_card,
        get_keyboard_func=get_keyboard,
        get_photo_func=get_photo,
        callback_prefix="exc_cards_page",
        page_title="Страница",
        parse_mode="Markdown",
        page_1_based=True
    )


async def send_private_excursions_cards_page(message: Message, state: FSMContext, page: int):
    """Отправить страницу с приватными экскурсиями (по 5 штук)"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("people_count", 1)

    if not excursions:
        return

    # Функция форматирования карточки
    def format_card(excursion):
        return get_private_excursion_card_text(excursion, people_count, expanded=False)

    # Функция создания клавиатуры с кнопками развернуть/свернуть и ссылкой
    def get_keyboard(excursion):
        buttons = [
            [InlineKeyboardButton(text="✅ Забронировать", callback_data=f"exc_book:{excursion['id']}")],
            [InlineKeyboardButton(text="Развернуть ▼", callback_data=f"exc_private_expand_page:{excursion['id']}:{page}")],
        ]

        # Добавляем кнопку "Смотреть экскурсию" если есть URL
        excursion_url = excursion.get("url")
        if excursion_url:
            buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", url=excursion_url)])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Функция получения фото
    async def get_photo(excursion):
        return await get_excursion_photo(excursion["id"])

    # Используем универсальную функцию
    await send_items_page(
        message=message,
        items=excursions,
        page=page,
        per_page=EXCURSIONS_PER_PAGE,
        format_card_func=format_card,
        get_keyboard_func=get_keyboard,
        get_photo_func=get_photo,
        callback_prefix="exc_private_cards_page",
        page_title="Страница",
        parse_mode="Markdown",
        page_1_based=True
    )


@router.callback_query(F.data == "exc_group:show_all")
async def show_all_group_excursions(callback: CallbackQuery, state: FSMContext):
    """Показать все групповые экскурсии страницей"""
    await callback.answer()

    data = await state.get_data()
    excursions = data.get("excursions", [])

    if not excursions:
        await callback.answer("Экскурсии не найдены", show_alert=True)
        return

    # Удаляем текущее сообщение (может быть с фото)
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.answer("⏳ Загружаю экскурсии...")

    try:
        # Отправляем первую страницу
        await send_excursions_cards_page(callback.message, state, page=1)

        # Удаляем сообщение о загрузке
        try:
            await loading_msg.delete()
        except:
            pass
    except Exception as e:
        logger.error(f"Ошибка при отображении экскурсий: {e}")
        await loading_msg.edit_text(
            "😔 Произошла ошибка при загрузке экскурсий.",
            reply_markup=get_back_to_main_keyboard()
        )


@router.callback_query(F.data.startswith("exc_cards_page:"))
async def navigate_excursions_pages(callback: CallbackQuery, state: FSMContext):
    """Переключение страниц экскурсий"""
    await callback.answer()

    # Получаем номер страницы
    page = int(callback.data.split(":")[1])

    # Удаляем контрольное сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем новую страницу
    await send_excursions_cards_page(callback.message, state, page)


@router.callback_query(F.data == "exc_group_month:back")
async def back_to_group_month_list(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку экскурсий за месяц"""
    await callback.answer()

    data = await state.get_data()
    year = data.get("group_month_year")
    month = data.get("group_month_month")
    page = data.get("group_month_page", 0)

    try:
        await callback.message.delete()
    except:
        pass

    await show_group_month_excursions_list(callback.message, state, year, month, page=page)


@router.callback_query(F.data.startswith("exc_group_month:"))
async def show_group_month_excursions(callback: CallbackQuery, state: FSMContext):
    """Показать все групповые экскурсии за месяц"""
    await callback.answer()

    month_str = callback.data.split(":")[1]
    year, month = map(int, month_str.split("-"))

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.answer(f"⏳ Загружаю экскурсии за {MONTH_NAMES[month-1]} {year}...")

    # Формируем дату первого дня месяца для запроса
    first_day_of_month = f"{year:04d}-{month:02d}-01"

    # Загружаем экскурсии, указав первый день месяца в запросе
    all_excursions = await get_data_loader().get_excursions_by_filters(
        island=None,  # Без фильтра по острову
        excursion_type="group",
        date=first_day_of_month  # Первый день месяца
    )

    # Фильтруем только экскурсии за нужный месяц/год
    excursions = []
    for exc in all_excursions:
        exc_date = exc.get("date")  # "YYYY-MM-DD"
        if exc_date:
            try:
                exc_dt = datetime.strptime(exc_date, "%Y-%m-%d")
                if exc_dt.year == year and exc_dt.month == month:
                    excursions.append(exc)
            except:
                pass

    if not excursions:
        try:
            await loading_msg.delete()
        except:
            pass
        await callback.answer(f"На {MONTH_NAMES_GENITIVE[month-1]} экскурсий не найдено", show_alert=True)
        return

    # ИСПРАВЛЕНИЕ: Дозагружаем цены для всех экскурсий за месяц
    logger.info(f"📊 Дозагрузка цен для {len(excursions)} экскурсий за месяц...")
    for excursion in excursions:
        if not excursion.get('price_usd') or excursion.get('price_usd') == 0:
            # Загружаем полные данные экскурсии с ценой
            full_excursion = await get_data_loader().get_excursion_by_id(excursion['id'])
            if full_excursion and full_excursion.get('price_usd'):
                excursion['price'] = full_excursion['price_usd']
                excursion['price_usd'] = full_excursion['price_usd']

    # Сохраняем данные
    await state.update_data(
        group_month_excursions=excursions,
        group_month_year=year,
        group_month_month=month,
        group_month_page=0
    )

    # Удаляем сообщения о загрузке и текущее сообщение
    try:
        await loading_msg.delete()
    except:
        pass
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем первую страницу
    await show_group_month_excursions_list(callback.message, state, year, month, page=0)


async def show_group_month_excursions_list(message: Message, state: FSMContext, year: int, month: int, page: int = 0):
    """Показать список групповых экскурсий за месяц с постраничным выводом"""
    data = await state.get_data()

    # Используем уже загруженные данные из state вместо повторной загрузки
    excursions = data.get("group_month_excursions", [])

    # Обновляем только страницу
    await state.update_data(group_month_page=page)

    # Формируем текст заголовка
    text = f"**Групповые экскурсии**\n{MONTH_NAMES[month-1]} {year}\n\n"

    if not excursions:
        text += "На выбранный месяц экскурсий пока нет."
        buttons = [
            [InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_type")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        # Постраничный вывод
        total_excursions = len(excursions)
        total_pages = (total_excursions + EXCURSIONS_PER_PAGE - 1) // EXCURSIONS_PER_PAGE

        # Нормализуем номер страницы
        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1

        # Получаем экскурсии для текущей страницы
        start_idx = page * EXCURSIONS_PER_PAGE
        end_idx = min(start_idx + EXCURSIONS_PER_PAGE, total_excursions)
        page_excursions = excursions[start_idx:end_idx]

        text += f"Показаны экскурсии {start_idx + 1}-{end_idx} из {total_excursions}\n\n"

        # Используем универсальную клавиатуру
        keyboard = get_month_excursions_list_keyboard(
            excursions=page_excursions,
            page=page,
            total_pages=total_pages,
            year=year,
            month=month,
            view_callback_prefix="exc_group_month_view",
            page_callback_prefix="exc_group_month_page",
            month_callback_prefix="exc_group_month",
            show_create_button=False,
            max_name_length=MAX_EXCURSION_NAME_LENGTH
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("exc_group_month_page:"))
async def navigate_group_month_page(callback: CallbackQuery, state: FSMContext):
    """Навигация по страницам экскурсий за месяц"""
    await callback.answer()

    page_str = callback.data.split(":")[1]

    if page_str == "ignore":
        return

    page = int(page_str)
    data = await state.get_data()
    year = data.get("group_month_year")
    month = data.get("group_month_month")

    try:
        await callback.message.delete()
    except:
        pass

    await show_group_month_excursions_list(callback.message, state, year, month, page=page)


@router.callback_query(F.data.startswith("exc_group_month_view:"))
async def view_group_month_excursion(callback: CallbackQuery, state: FSMContext):
    """Просмотр детальной информации об экскурсии из месячного списка"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]

    # Сначала пробуем найти экскурсию в уже загруженных данных (с датой)
    data = await state.get_data()
    group_month_excursions = data.get("group_month_excursions", [])
    people_count = data.get("excursion_people_count", 1)

    excursion = None
    for exc in group_month_excursions:
        if exc.get("id") == excursion_id:
            excursion = exc
            break

    # Если не нашли - загружаем из API (но дата может быть некорректной)
    if not excursion:
        excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    # Показываем детальную карточку
    card_text = get_group_excursion_card_text(excursion, people_count, expanded=False)
    keyboard = get_group_month_excursion_detail_keyboard(excursion['id'])

    # Используем универсальную функцию отправки
    await send_excursion_card_with_photo(callback.message, card_text, keyboard, excursion["id"])


@router.callback_query(F.data.startswith("exc_join:"))
async def join_group_excursion(callback: CallbackQuery, state: FSMContext):
    """Присоединиться к групповой экскурсии"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]
    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    # Получаем количество людей из state (уже было введено ранее)
    data = await state.get_data()
    people_count = data.get("excursion_people_count", 1)

    # Сохраняем ID и дату экскурсии
    excursion_date = excursion.get("date")
    await state.update_data(
        selected_excursion_id=excursion_id,
        excursion_date=excursion_date
    )

    # Показываем форму для ввода контактных данных
    keyboard = get_action_choice_keyboard("group")
    await callback.message.answer(
        get_excursion_booking_text(excursion["name"], people_count, excursion_date),
        reply_markup=keyboard
    )


# ========== ВЕТКА B: Индивидуальные экскурсии ==========

@router.callback_query(UserStates.EXCURSIONS_SELECT_TYPE, F.data == "exc_type:private")
async def select_private_excursions(callback: CallbackQuery, state: FSMContext):
    """Выбор индивидуальных экскурсий - показываем выбор острова"""
    await callback.answer()

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.edit_text("⏳ Загружаю доступные острова с экскурсиями...")

    try:
        # Загружаем все острова с подсчётом экскурсий
        islands = await get_data_loader().excursions_loader.get_available_islands_with_count()

        if not islands:
            await loading_msg.edit_text(
                "😔 К сожалению, не удалось загрузить список островов с экскурсиями. Попробуйте позже.",
                reply_markup=get_back_to_main_keyboard()
            )
            return

        # Показываем клавиатуру выбора острова
        await loading_msg.edit_text(
            f"**Индивидуальные экскурсии**\n\n"
            f"Выберите остров для поиска экскурсий:\n"
            f"_(Всего найдено {len(islands)} островов с экскурсиями)_",
            reply_markup=get_private_islands_keyboard(islands),
            parse_mode="Markdown"
        )

        await state.set_state(UserStates.EXCURSIONS_PRIVATE_SELECT_ISLAND)

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки островов для индивидуальных экскурсий: {e}")
        await loading_msg.edit_text(
            "😔 Произошла ошибка при загрузке списка островов.",
            reply_markup=get_back_to_main_keyboard()
        )


@router.callback_query(UserStates.EXCURSIONS_PRIVATE_SELECT_ISLAND, F.data.startswith("private_island:"))
async def select_private_island(callback: CallbackQuery, state: FSMContext):
    """Выбор острова для индивидуальных экскурсий - запрашиваем количество людей"""
    await callback.answer()

    location_id = int(callback.data.split(":")[1])

    # Сохраняем location_id как island в state (для совместимости с существующим кодом)
    await state.update_data(island=str(location_id))

    # Запрашиваем количество человек с клавиатурой
    await callback.message.edit_text(
        EXCURSIONS_PRIVATE_INTRO,
        reply_markup=get_people_count_keyboard()
    )

    await state.set_state(UserStates.EXCURSIONS_PRIVATE_INPUT_PEOPLE)


async def show_private_excursion(message: Message, state: FSMContext, index: int, expanded: bool = False):
    """Показать карточку индивидуальной экскурсии"""
    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("people_count", 1)

    if not excursions or index >= len(excursions):
        return

    excursion = excursions[index]
    card_text = get_private_excursion_card_text(excursion, people_count, expanded)

    keyboard = get_private_excursion_keyboard(
        excursion["id"],
        index,
        len(excursions),
        expanded,
        excursion.get("url")
    )

    # Пытаемся получить фото
    photo = await get_excursion_photo(excursion["id"])

    # Telegram ограничивает caption до 1024 символов
    MAX_CAPTION_LENGTH = 1024
    if len(card_text) > MAX_CAPTION_LENGTH:
        card_text = card_text[:MAX_CAPTION_LENGTH - 3] + "..."

    if photo:
        try:
            await message.answer_photo(
                photo=photo,
                caption=card_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить фото для экскурсии: {e}")
            # Если не удалось отправить с фото - отправляем без фото
            await message.answer(
                card_text,
                reply_markup=keyboard
            )
    else:
        await message.answer(
            card_text,
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("exc_private_expand:"))
async def expand_private_excursion(callback: CallbackQuery, state: FSMContext):
    """Развернуть описание индивидуальной экскурсии"""
    await callback.answer()

    index = int(callback.data.split(":")[2])
    
    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем развернутую версию
    await show_private_excursion(callback.message, state, index, expanded=True)


@router.callback_query(F.data.startswith("exc_private_collapse:"))
async def collapse_private_excursion(callback: CallbackQuery, state: FSMContext):
    """Свернуть описание индивидуальной экскурсии"""
    await callback.answer()

    index = int(callback.data.split(":")[2])
    
    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем свернутую версию
    await show_private_excursion(callback.message, state, index, expanded=False)


@router.callback_query(UserStates.EXCURSIONS_SHOW_RESULTS, F.data.startswith("exc_nav:"))
async def navigate_private_excursions(callback: CallbackQuery, state: FSMContext):
    """Навигация по индивидуальным экскурсиям"""
    await callback.answer()

    parts = callback.data.split(":")
    direction = parts[1]
    current_index = int(parts[2])

    new_index = current_index - 1 if direction == "prev" else current_index + 1

    await state.update_data(current_excursion_index=new_index)

    try:
        await callback.message.delete()
    except:
        pass

    await show_private_excursion(callback.message, state, new_index)


@router.callback_query(F.data == "exc_private:show_all")
async def show_all_private_excursions(callback: CallbackQuery, state: FSMContext):
    """Показать все приватные экскурсии страницей"""
    await callback.answer()

    data = await state.get_data()
    excursions = data.get("excursions", [])

    if not excursions:
        await callback.answer("Экскурсии не найдены", show_alert=True)
        return

    # Удаляем текущее сообщение (может быть с фото)
    try:
        await callback.message.delete()
    except:
        pass

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.answer("⏳ Загружаю экскурсии...")

    try:
        # Отправляем первую страницу
        await send_private_excursions_cards_page(callback.message, state, page=1)

        # Удаляем сообщение о загрузке
        try:
            await loading_msg.delete()
        except:
            pass
    except Exception as e:
        logger.error(f"Ошибка при отображении экскурсий: {e}")
        await loading_msg.edit_text(
            "😔 Произошла ошибка при загрузке экскурсий.",
            reply_markup=get_back_to_main_keyboard()
        )


@router.callback_query(F.data.startswith("exc_private_cards_page:"))
async def navigate_private_excursions_pages(callback: CallbackQuery, state: FSMContext):
    """Переключение страниц приватных экскурсий"""
    await callback.answer()

    # Получаем номер страницы
    page = int(callback.data.split(":")[1])

    # Удаляем контрольное сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем новую страницу
    await send_private_excursions_cards_page(callback.message, state, page)


@router.callback_query(F.data.startswith("exc_private_expand_page:"))
async def expand_private_excursion_in_page(callback: CallbackQuery, state: FSMContext):
    """Развернуть описание экскурсии в постраничном выводе"""
    await callback.answer()

    parts = callback.data.split(":")
    excursion_id = parts[1]
    page = int(parts[2])

    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("people_count", 1)

    # Находим экскурсию по ID
    excursion = None
    for exc in excursions:
        if exc.get("id") == excursion_id:
            excursion = exc
            break

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    # Формируем развернутый текст
    card_text = get_private_excursion_card_text(excursion, people_count, expanded=True)

    # Создаем клавиатуру с кнопкой "Свернуть"
    buttons = [
        [InlineKeyboardButton(text="✅ Забронировать", callback_data=f"exc_book:{excursion['id']}")],
        [InlineKeyboardButton(text="Свернуть ▲", callback_data=f"exc_private_collapse_page:{excursion['id']}:{page}")],
    ]

    # Добавляем кнопку "Смотреть экскурсию" если есть URL
    excursion_url = excursion.get("url")
    if excursion_url:
        buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", url=excursion_url)])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Обновляем сообщение
    try:
        await callback.message.edit_caption(
            caption=card_text,
            reply_markup=keyboard
        )
    except:
        # Если нет фото, пробуем обновить текст
        try:
            await callback.message.edit_text(
                text=card_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения: {e}")


@router.callback_query(F.data.startswith("exc_private_collapse_page:"))
async def collapse_private_excursion_in_page(callback: CallbackQuery, state: FSMContext):
    """Свернуть описание экскурсии в постраничном выводе"""
    await callback.answer()

    parts = callback.data.split(":")
    excursion_id = parts[1]
    page = int(parts[2])

    data = await state.get_data()
    excursions = data.get("excursions", [])
    people_count = data.get("people_count", 1)

    # Находим экскурсию по ID
    excursion = None
    for exc in excursions:
        if exc.get("id") == excursion_id:
            excursion = exc
            break

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    # Формируем свернутый текст
    card_text = get_private_excursion_card_text(excursion, people_count, expanded=False)

    # Создаем клавиатуру с кнопкой "Развернуть"
    buttons = [
        [InlineKeyboardButton(text="✅ Забронировать", callback_data=f"exc_book:{excursion['id']}")],
        [InlineKeyboardButton(text="Развернуть ▼", callback_data=f"exc_private_expand_page:{excursion['id']}:{page}")],
    ]

    # Добавляем кнопку "Смотреть экскурсию" если есть URL
    excursion_url = excursion.get("url")
    if excursion_url:
        buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", url=excursion_url)])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Обновляем сообщение
    try:
        await callback.message.edit_caption(
            caption=card_text,
            reply_markup=keyboard
        )
    except:
        # Если нет фото, пробуем обновить текст
        try:
            await callback.message.edit_text(
                text=card_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка обновления сообщения: {e}")


@router.callback_query(UserStates.EXCURSIONS_SHOW_RESULTS, F.data.startswith("exc_book:"))
async def book_private_excursion(callback: CallbackQuery, state: FSMContext):
    """Бронирование индивидуальной экскурсии"""
    await callback.answer()
    
    excursion_id = callback.data.split(":")[1]
    await state.update_data(selected_excursion_id=excursion_id)

    # Показываем календарь выбора даты
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month, back_callback="excursions:back_private_from_calendar")

    await callback.message.answer(
        "Выберите дату:",
        reply_markup=calendar
    )

    await state.set_state(UserStates.EXCURSIONS_PRIVATE_SELECT_DATE)


@router.callback_query(UserStates.EXCURSIONS_PRIVATE_SELECT_DATE, F.data.startswith("cal:"))
async def navigate_private_calendar(callback: CallbackQuery):
    """Навигация по календарю для индивидуальных экскурсий"""
    await callback.answer()

    date_str = callback.data.split(":")[1]

    if date_str == "ignore":
        return

    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month, back_callback="excursions:back_private_from_calendar")

    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.EXCURSIONS_PRIVATE_SELECT_DATE, F.data.startswith("date:"))
async def select_private_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для индивидуальной экскурсии"""
    await callback.answer()

    date = callback.data.split(":")[1]

    data = await state.get_data()
    excursion_id = data.get("selected_excursion_id")
    people_count = data.get("people_count")

    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    await state.update_data(excursion_people_count=people_count)

    # Используем универсальную клавиатуру
    keyboard = get_action_choice_keyboard("private")

    await callback.message.edit_text(
        get_excursion_booking_text(excursion["name"], people_count, format_date(date)),
        reply_markup=keyboard
    )


# ========== ВЕТКА C: Поиск попутчиков ==========

@router.callback_query(UserStates.EXCURSIONS_SELECT_TYPE, F.data == "exc_type:companions")
async def select_companions(callback: CallbackQuery, state: FSMContext):
    """Поиск попутчиков"""
    await callback.answer()
    
    await callback.message.edit_text(COMPANIONS_INTRO)
    
    # Показываем список за текущий месяц
    now = datetime.now()
    await show_companions_list(callback.message, state, now.year, now.month)
    
    await state.set_state(UserStates.COMPANIONS_VIEW_LIST)


async def show_companions_list(message: Message, state: FSMContext, year: int, month: int, page: int = 0):
    """Показать список экскурсий с поиском попутчиков"""
    # ИЗМЕНЕНО: Попутчики теперь загружаются БЕЗ фильтра по острову (все острова)
    # Получаем экскурсии за месяц
    excursions = await get_data_loader().get_companions_by_month(None, year, month)
    
    await state.update_data(
        companions_month=month,
        companions_year=year,
        companions_excursions=excursions,
        companions_page=page
    )

    # Формируем текст заголовка
    text = f"**Экскурсии с поиском попутчиков**\n{MONTH_NAMES[month-1]} {year}\n\n"

    if not excursions:
        text += "На выбранный месяц экскурсий пока нет."
        keyboard = get_companions_list_keyboard(month, year)

        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        # Постраничный вывод
        total_excursions = len(excursions)
        total_pages = (total_excursions + EXCURSIONS_PER_PAGE - 1) // EXCURSIONS_PER_PAGE

        # Нормализуем номер страницы
        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1

        # Получаем экскурсии для текущей страницы
        start_idx = page * EXCURSIONS_PER_PAGE
        end_idx = min(start_idx + EXCURSIONS_PER_PAGE, total_excursions)
        page_excursions = excursions[start_idx:end_idx]

        text += f"Показаны экскурсии {start_idx + 1}-{end_idx} из {total_excursions}\n\n"

        # Используем универсальную клавиатуру
        keyboard = get_month_excursions_list_keyboard(
            excursions=page_excursions,
            page=page,
            total_pages=total_pages,
            year=year,
            month=month,
            view_callback_prefix="comp_view",
            page_callback_prefix="comp_page",
            month_callback_prefix="comp_month",
            show_create_button=True,
            max_name_length=MAX_EXCURSION_NAME_LENGTH
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("comp_view:"))
async def view_companion_excursion(callback: CallbackQuery, state: FSMContext):
    """Просмотр детальной информации об экскурсии с попутчиками"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]

    # ИСПРАВЛЕНО: Всегда загружаем полные данные с API для получения списка попутчиков (slst)
    # Краткий список содержит только базовую информацию без контактов участников
    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        # Если не удалось загрузить из API, пробуем взять из кэша
        data = await state.get_data()
        companions_excursions = data.get("companions_excursions", [])
        for exc in companions_excursions:
            if exc.get("id") == excursion_id:
                excursion = exc
                break

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    # Показываем детальную карточку
    card_text = get_companions_excursion_card_text(excursion)
    keyboard = get_companions_excursion_keyboard(excursion_id, excursion.get("url"))

    await callback.message.answer(
        card_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("comp_join:"))
async def join_companion_excursion(callback: CallbackQuery, state: FSMContext):
    """Присоединиться к экскурсии с попутчиками - запрашиваем количество людей"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]
    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        return

    # Сохраняем ID экскурсии
    await state.update_data(selected_excursion_id=excursion_id)

    # Запрашиваем количество человек с клавиатурой
    await callback.message.answer(
        "Сколько человек присоединяется к экскурсии?",
        reply_markup=get_people_count_keyboard()
    )

    await state.set_state(UserStates.COMPANIONS_JOIN_INPUT_PEOPLE)


@router.callback_query(F.data == "comp_back:list")
async def back_to_companions_list(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку попутчиков"""
    await callback.answer()

    data = await state.get_data()
    year = data.get("companions_year", datetime.now().year)
    month = data.get("companions_month", datetime.now().month)
    page = data.get("companions_page", 0)

    try:
        await callback.message.delete()
    except:
        pass

    await show_companions_list(callback.message, state, year, month, page=page)

    await state.set_state(UserStates.COMPANIONS_VIEW_LIST)


@router.callback_query(F.data.startswith("comp_month:"))
async def navigate_companions_month(callback: CallbackQuery, state: FSMContext):
    """Навигация по месяцам для попутчиков"""
    await callback.answer()

    month_str = callback.data.split(":")[1]

    if month_str == "ignore":
        return

    year, month = map(int, month_str.split("-"))

    try:
        await callback.message.delete()
    except:
        pass

    await show_companions_list(callback.message, state, year, month, page=0)


@router.callback_query(F.data.startswith("comp_page:"))
async def navigate_companions_page(callback: CallbackQuery, state: FSMContext):
    """Навигация по страницам экскурсий с попутчиками"""
    await callback.answer()

    page_str = callback.data.split(":")[1]

    if page_str == "ignore":
        return

    page = int(page_str)
    data = await state.get_data()
    year = data.get("companions_year")
    month = data.get("companions_month")

    try:
        await callback.message.delete()
    except:
        pass

    await show_companions_list(callback.message, state, year, month, page=page)


@router.callback_query(F.data == "comp_create:start")
async def create_companion_request_start(callback: CallbackQuery):
    """Начало создания заявки на поиск попутчиков"""
    await callback.answer()
    
    await callback.message.answer(
        COMPANIONS_HOW_IT_WORKS,
        reply_markup=get_companions_create_agree_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "comp_create:agree")
async def create_companion_agree(callback: CallbackQuery, state: FSMContext):
    """Согласие с условиями поиска попутчиков - запрашиваем количество человек"""
    await callback.answer()

    # Запрашиваем количество человек с клавиатурой
    await callback.message.edit_text(
        COMPANIONS_INPUT_PEOPLE,
        reply_markup=get_people_count_keyboard()
    )

    await state.set_state(UserStates.COMPANIONS_CREATE_INPUT_PEOPLE)


@router.message(UserStates.COMPANIONS_CREATE_INPUT_PEOPLE, F.text)
async def process_companion_people_count(message: Message, state: FSMContext):
    """Обработка количества человек для заявки - показываем выбор острова"""
    try:
        people_count = int(message.text.strip())

        if people_count < 1:
            raise ValueError

        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass

        # Сохраняем количество людей
        await state.update_data(people_count=people_count)

        # Показываем сообщение о загрузке
        loading_msg = await message.answer("⏳ Загружаю доступные острова с экскурсиями...")

        try:
            # Загружаем все острова с подсчётом экскурсий (используем тот же метод что и для private)
            islands = await get_data_loader().excursions_loader.get_available_islands_with_count()

            if not islands:
                await loading_msg.edit_text(
                    "😔 К сожалению, не удалось загрузить список островов с экскурсиями. Попробуйте позже.",
                    reply_markup=get_back_to_main_keyboard()
                )
                return

            # Показываем клавиатуру выбора острова
            await loading_msg.edit_text(
                f"**Создание заявки на поиск попутчиков**\n\n"
                f"Выберите остров для поиска экскурсий:\n"
                f"_(Всего найдено {len(islands)} островов с экскурсиями)_",
                reply_markup=get_private_islands_keyboard(islands),
                parse_mode="Markdown"
            )

            await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_ISLAND)

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки островов для создания заявки на попутчиков: {e}")
            await loading_msg.edit_text(
                "😔 Произошла ошибка при загрузке списка островов.",
                reply_markup=get_back_to_main_keyboard()
            )

    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число",
            reply_markup=get_back_to_main_keyboard()
        )


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION, F.data.startswith("exc_nav:"))
async def navigate_companion_excursions(callback: CallbackQuery, state: FSMContext):
    """Навигация по индивидуальным экскурсиям при создании заявки"""
    await callback.answer()

    parts = callback.data.split(":")
    direction = parts[1]
    current_index = int(parts[2])

    new_index = current_index - 1 if direction == "prev" else current_index + 1

    await state.update_data(current_excursion_index=new_index)

    try:
        await callback.message.delete()
    except:
        pass

    await show_private_excursion(callback.message, state, new_index)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION, F.data.startswith("exc_book:"))
async def select_excursion_for_companion(callback: CallbackQuery, state: FSMContext):
    """Выбор экскурсии для создания заявки - показываем календарь"""
    await callback.answer()

    excursion_id = callback.data.split(":")[1]
    await state.update_data(selected_excursion_id=excursion_id)

    # Показываем календарь выбора даты
    now = datetime.now()
    calendar = get_calendar_keyboard(now.year, now.month, back_callback="excursions:back_companion_from_calendar")

    await callback.message.answer(
        COMPANIONS_SELECT_DATE,
        reply_markup=calendar
    )

    await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_DATE)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_DATE, F.data.startswith("cal:"))
async def navigate_companion_calendar(callback: CallbackQuery):
    """Навигация по календарю для создания заявки"""
    await callback.answer()

    date_str = callback.data.split(":")[1]

    if date_str == "ignore":
        return

    year, month = map(int, date_str.split("-"))
    calendar = get_calendar_keyboard(year, month, back_callback="excursions:back_companion_from_calendar")

    await callback.message.edit_reply_markup(reply_markup=calendar)


@router.callback_query(UserStates.COMPANIONS_CREATE_SELECT_DATE, F.data.startswith("date:"))
async def select_date_for_companion(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для заявки - показываем выбор действия"""
    await callback.answer()

    date = callback.data.split(":")[1]

    data = await state.get_data()
    excursion_id = data.get("selected_excursion_id")
    people_count = data.get("people_count")

    excursion = await get_data_loader().get_excursion_by_id(excursion_id)

    if not excursion:
        await callback.answer("❌ Экскурсия не найдена", show_alert=True)
        return

    # Сохраняем данные в состоянии (для последующего использования)
    await state.update_data(
        companion_date=date,
        excursion_people_count=people_count
    )

    # Формируем текст с информацией об экскурсии
    text = (
        f"**{excursion['name']}**\n\n"
        f"📅 Дата: {format_date(date)}\n"
        f"👥 Количество человек: {people_count}\n\n"
        f"Что хотите сделать?"
    )

    # Показываем клавиатуру выбора действия (как для групповых экскурсий)
    keyboard = get_action_choice_keyboard("create")

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )


@router.callback_query(
    UserStates.COMPANIONS_CREATE_SELECT_ISLAND,
    F.data.startswith("private_island:")
)
async def select_companion_island(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора острова для создания заявки на попутчиков - загружаем экскурсии"""
    await callback.answer()

    location_id = int(callback.data.split(":")[1])

    # Сохраняем location_id как island в state
    await state.update_data(island=str(location_id))

    island = str(location_id)

    # Показываем сообщение о загрузке
    loading_msg = await callback.message.edit_text("⏳ Загружаю индивидуальные экскурсии...")

    try:
        # Получаем ТОЛЬКО индивидуальные экскурсии для выбранного острова
        excursions = await get_data_loader().get_excursions_by_filters(
            island=island,
            excursion_type="private"
        )

        if not excursions:
            await loading_msg.edit_text(
                "😔 К сожалению, индивидуальных экскурсий на этом острове не найдено.",
                reply_markup=get_back_to_main_keyboard()
            )
            return

        await state.update_data(
            excursions=excursions,
            current_excursion_index=0
        )

        # Удаляем сообщение о загрузке
        try:
            await loading_msg.delete()
        except:
            pass

        # Показываем первую экскурсию (используем функцию из ветки private)
        await show_private_excursion(callback.message, state, 0)

        await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки экскурсий для острова {island}: {e}")
        await loading_msg.edit_text(
            "😔 Произошла ошибка при загрузке экскурсий.",
            reply_markup=get_back_to_main_keyboard()
        )


# ========== Добавление в заказ и бронирование ==========

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

    await show_private_excursion(callback.message, state, current_index)

    await state.set_state(UserStates.COMPANIONS_CREATE_SELECT_EXCURSION)