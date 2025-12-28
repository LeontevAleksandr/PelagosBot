"""Клавиатуры для флоу экскурсий"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_excursion_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа экскурсии"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Групповые", callback_data="exc_type:group")],
        [InlineKeyboardButton(text="👤 Индивидуальные", callback_data="exc_type:private")],
        [InlineKeyboardButton(text="🔍 Поиск попутчиков", callback_data="exc_type:companions")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ])
    return keyboard


def get_group_excursion_keyboard(excursion_id: str, has_prev: bool, has_next: bool, current_date: str, expanded: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для групповой экскурсии"""
    buttons = []
    
    # Кнопка присоединиться
    buttons.append([InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"exc_join:{excursion_id}")])
    
    # Кнопка развернуть/свернуть
    if expanded:
        buttons.append([InlineKeyboardButton(text="Свернуть ▲", callback_data=f"exc_collapse:{excursion_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="Развернуть ▼", callback_data=f"exc_expand:{excursion_id}")])
    
    # Навигация по датам
    nav_buttons = []
    if has_prev:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущий день", callback_data=f"exc_date:prev:{current_date}"))
    if has_next:
        nav_buttons.append(InlineKeyboardButton(text="Следующий день ➡️", callback_data=f"exc_date:next:{current_date}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_no_group_excursions_keyboard(selected_date: str = None) -> InlineKeyboardMarkup:
    """
    Клавиатура когда нет групповых экскурсий

    Args:
        selected_date: дата в формате YYYY-MM-DD для кнопки "Экскурсии на месяц"
    """
    buttons = []

    # Кнопка показать экскурсии на весь месяц
    if selected_date:
        from datetime import datetime
        dt = datetime.strptime(selected_date, "%Y-%m-%d")
        month_names_genitive = [
            "январь", "февраль", "март", "апрель", "май", "июнь",
            "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
        ]
        month_name = month_names_genitive[dt.month - 1]
        buttons.append([InlineKeyboardButton(
            text=f"📅 Экскурсии на {month_name}",
            callback_data=f"exc_group_month:{dt.year}-{dt.month:02d}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_type")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_private_excursion_keyboard(excursion_id: str, current_index: int, total: int, expanded: bool = False, excursion_url: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для индивидуальной экскурсии"""
    buttons = []

    # Кнопка бронирования
    buttons.append([InlineKeyboardButton(text="✅ Забронировать", callback_data=f"exc_book:{excursion_id}")])

    # Кнопка развернуть/свернуть
    if expanded:
        buttons.append([InlineKeyboardButton(text="Свернуть ▲", callback_data=f"exc_private_collapse:{excursion_id}:{current_index}")])
    else:
        buttons.append([InlineKeyboardButton(text="Развернуть ▼", callback_data=f"exc_private_expand:{excursion_id}:{current_index}")])

    # Навигация
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"exc_nav:prev:{current_index}"))
    if current_index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"exc_nav:next:{current_index}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    # Кнопка показать все страницей (если больше 1 экскурсии)
    if total > 1:
        buttons.append([InlineKeyboardButton(text="📋 Показать все страницей", callback_data="exc_private:show_all")])

    # Кнопка "Смотреть экскурсию" - URL или заглушка
    if excursion_url:
        buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", url=excursion_url)])
    else:
        buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", callback_data=f"exc_view:{excursion_id}")])

    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_companions_list_keyboard(month: int, year: int) -> InlineKeyboardMarkup:
    """Клавиатура для списка попутчиков с навигацией по месяцам"""
    from datetime import datetime
    
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    buttons = []
    
    # Навигация по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    buttons.append([
        InlineKeyboardButton(text="⬅️", callback_data=f"comp_month:{prev_year}-{prev_month:02d}"),
        InlineKeyboardButton(text=f"{month_names[month-1]} {year}", callback_data="comp_month:ignore"),
        InlineKeyboardButton(text="➡️", callback_data=f"comp_month:{next_year}-{next_month:02d}")
    ])
    
    buttons.append([InlineKeyboardButton(text="➕ Создать свою заявку", callback_data="comp_create:start")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_type")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_companions_excursion_keyboard(excursion_id: str, excursion_url: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для экскурсии с поиском попутчиков"""
    buttons = [
        [InlineKeyboardButton(text="✅ Записаться", callback_data=f"comp_join:{excursion_id}")],
        [InlineKeyboardButton(text="➕ Создать свою заявку", callback_data="comp_create:start")],
    ]
    
    # Кнопка "Смотреть экскурсию"
    if excursion_url:
        buttons.append([InlineKeyboardButton(text="🔍 Смотреть экскурсию", url=excursion_url)])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="comp_back:list")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_companions_create_agree_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура согласия с условиями поиска попутчиков"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен, продолжить", callback_data="comp_create:agree")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="comp_back:list")]
    ])
    return keyboard


def get_companions_select_excursion_keyboard(excursions: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора экскурсии при создании заявки попутчика"""
    buttons = []

    # Добавляем кнопку для каждой экскурсии
    for exc in excursions:
        # Обрезаем длинные названия для кнопок
        button_text = exc['name'][:40] + "..." if len(exc['name']) > 40 else exc['name']
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"comp_select_exc:{exc['id']}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="comp_back:list")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_group_excursion_full_keyboard(
    excursion_id: str,
    index: int,
    has_prev: bool,
    has_next: bool,
    current_date: str,
    expanded: bool = False
) -> InlineKeyboardMarkup:
    """
    Полная клавиатура для групповой экскурсии с навигацией и показом месяца

    Args:
        excursion_id: ID экскурсии
        index: индекс текущей экскурсии
        has_prev: есть ли предыдущая экскурсия
        has_next: есть ли следующая экскурсия
        current_date: текущая дата в формате YYYY-MM-DD
        expanded: развёрнута ли карточка
    """
    from datetime import datetime

    # Названия месяцев в родительном падеже
    MONTH_NAMES_GENITIVE = [
        "январь", "февраль", "март", "апрель", "май", "июнь",
        "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
    ]

    buttons = []

    # Кнопка присоединиться
    buttons.append([InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"exc_join:{excursion_id}")])

    # Кнопка развернуть/свернуть
    if expanded:
        buttons.append([InlineKeyboardButton(text="Свернуть ▲", callback_data=f"exc_group_collapse:{index}")])
    else:
        buttons.append([InlineKeyboardButton(text="Развернуть ▼", callback_data=f"exc_group_expand:{index}")])

    # Пагинация между экскурсиями на одну дату
    if has_prev or has_next:
        nav_buttons = []
        if has_prev:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"exc_group_nav:prev:{index}"))
        if has_next:
            nav_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"exc_group_nav:next:{index}"))
        buttons.append(nav_buttons)

    # Кнопка показать все страницей
    buttons.append([InlineKeyboardButton(text="📋 Показать все страницей", callback_data="exc_group:show_all")])

    # Кнопка показать экскурсии на весь месяц
    if current_date:
        dt = datetime.strptime(current_date, "%Y-%m-%d")
        month_name = MONTH_NAMES_GENITIVE[dt.month - 1]
        buttons.append([InlineKeyboardButton(
            text=f"📅 Экскурсии на {month_name}",
            callback_data=f"exc_group_month:{dt.year}-{dt.month:02d}"
        )])

    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_action_choice_keyboard(excursion_type: str) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура выбора действия (добавить в заказ / забронировать)

    Args:
        excursion_type: тип экскурсии (group, private, companion, create)
    """
    buttons = [
        [InlineKeyboardButton(text="🛒 Добавить в заказ", callback_data=f"exc_{excursion_type}:add_to_order")],
        [InlineKeyboardButton(text="✅ Забронировать сейчас", callback_data=f"exc_{excursion_type}:book_now")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_group_month_excursion_detail_keyboard(excursion_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра одной экскурсии из месячного списка"""
    buttons = [
        [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"exc_join:{excursion_id}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="exc_group_month:back")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_month_excursions_list_keyboard(
    excursions: list,
    page: int,
    total_pages: int,
    year: int,
    month: int,
    view_callback_prefix: str,
    page_callback_prefix: str,
    month_callback_prefix: str,
    show_create_button: bool = False,
    max_name_length: int = 40
) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура для списка экскурсий за месяц с постраничной навигацией

    Args:
        excursions: Список экскурсий для текущей страницы
        page: Текущая страница (0-based)
        total_pages: Общее количество страниц
        year: Год
        month: Месяц
        view_callback_prefix: Префикс для просмотра экскурсии (напр. "exc_group_month_view" или "comp_view")
        page_callback_prefix: Префикс для навигации по страницам (напр. "exc_group_month_page" или "comp_page")
        month_callback_prefix: Префикс для навигации по месяцам (напр. "exc_group_month" или "comp_month")
        show_create_button: Показывать ли кнопку "Создать свою заявку"
        max_name_length: Максимальная длина названия в кнопке
    """
    from utils.helpers import format_date

    buttons = []

    # Формируем кнопки для каждой экскурсии на странице
    for exc in excursions:
        # Текст кнопки: дата + остров + название (обрезаем если длинное)
        island_name = exc.get('island_name', '')

        # Форматируем дату без года для компактности (dd.mm вместо dd.mm.yyyy)
        try:
            from datetime import datetime as dt
            date_obj = dt.strptime(exc['date'], "%Y-%m-%d")
            date_short = date_obj.strftime("%d.%m")
        except:
            date_short = format_date(exc['date'])

        # Формируем текст с учётом острова
        if island_name:
            button_text = f"📅 {date_short} - {island_name} - {exc['name'][:max_name_length]}"
        else:
            button_text = f"📅 {date_short} - {exc['name'][:max_name_length]}"

        if len(exc['name']) > max_name_length:
            button_text += "..."

        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"{view_callback_prefix}:{exc['id']}"
        )])

    # Навигация по страницам (если больше одной страницы)
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"{page_callback_prefix}:{page-1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data=f"{page_callback_prefix}:ignore"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="След ➡️", callback_data=f"{page_callback_prefix}:{page+1}"))
        buttons.append(nav_buttons)

    # Навигация по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    buttons.append([
        InlineKeyboardButton(text="◀️ Пред. месяц", callback_data=f"{month_callback_prefix}:{prev_year}-{prev_month:02d}"),
        InlineKeyboardButton(text="След. месяц ▶️", callback_data=f"{month_callback_prefix}:{next_year}-{next_month:02d}")
    ])

    # Кнопка создания заявки (только для попутчиков)
    if show_create_button:
        buttons.append([InlineKeyboardButton(text="➕ Создать свою заявку", callback_data="comp_create:start")])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_type")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_private_islands_keyboard(islands: list) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора острова для индивидуальных экскурсий

    Args:
        islands: список островов [{"location_id": int, "name": str, "count": int}, ...]
                 уже отсортирован по количеству экскурсий
    """
    buttons = []

    # Кнопки островов (по 2 в ряд) с количеством экскурсий
    for i in range(0, len(islands), 2):
        row = []

        island1 = islands[i]
        button_text1 = f"{island1['name']} ({island1['count']})"
        row.append(InlineKeyboardButton(
            text=button_text1,
            callback_data=f"private_island:{island1['location_id']}"
        ))

        if i + 1 < len(islands):
            island2 = islands[i + 1]
            button_text2 = f"{island2['name']} ({island2['count']})"
            row.append(InlineKeyboardButton(
                text=button_text2,
                callback_data=f"private_island:{island2['location_id']}"
            ))

        buttons.append(row)

    # Кнопки назад
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="excursions:back_to_type")])
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)