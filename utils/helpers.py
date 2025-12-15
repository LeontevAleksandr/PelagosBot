"""Вспомогательные функции"""
import re
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import requests


def validate_price_range(text: str, currency: str = "usd") -> tuple[bool, int, int]:
    """
    Валидация формата диапазона цен с учетом валюты
    Возвращает: (валидно, min_price, max_price)

    Args:
        text: Текст диапазона в формате "min-max"
        currency: Валюта для валидации ("usd", "rub", "peso")
    """
    pattern = r'^(\d+)-(\d+)$'
    match = re.match(pattern, text.strip())

    if not match:
        return False, 0, 0

    min_price = int(match.group(1))
    max_price = int(match.group(2))

    # Проверка логики
    if min_price >= max_price:
        return False, 0, 0

    # Получаем курсы валют
    rates = get_exchange_rates()

    # Минимальная и максимальная цена в USD
    min_usd_limit = 5
    max_usd_limit = 1000

    # Конвертируем в выбранную валюту для проверки границ
    min_currency_limit = int(min_usd_limit * rates[currency])
    max_currency_limit = int(max_usd_limit * rates[currency])

    # Проверяем границы в выбранной валюте
    if min_price < min_currency_limit or max_price > max_currency_limit:
        return False, 0, 0

    return True, min_price, max_price


def format_date(date_str: str) -> str:
    """Форматирование даты в читаемый вид"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%d.%m.%Y")
    except:
        return date_str


def get_calendar_keyboard(year: int, month: int, selected_date: str = None, min_date: str = None, back_callback: str = "hotels:back_from_calendar") -> InlineKeyboardMarkup:
    """
    Генерация inline календаря

    Args:
        year: год
        month: месяц (1-12)
        selected_date: уже выбранная дата (для выезда, чтобы блокировать прошлые даты)
        min_date: минимальная допустимая дата в формате YYYY-MM-DD
        back_callback: callback_data для кнопки "Назад"
    """
    import calendar
    
    # Определяем минимальную дату
    if min_date:
        min_datetime = datetime.strptime(min_date, "%Y-%m-%d")
    else:
        min_datetime = datetime.now()
    
    # Если выбрана дата заезда, минимальная дата выезда = заезд + 1 день
    if selected_date:
        selected_datetime = datetime.strptime(selected_date, "%Y-%m-%d")
        min_datetime = selected_datetime + timedelta(days=1)
    
    # Заголовок с месяцем и годом
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    buttons = []
    
    # Навигация по месяцам
    nav_row = []
    # Кнопка "предыдущий месяц"
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"cal:{prev_year}-{prev_month:02d}"))
    
    # Название месяца
    nav_row.append(InlineKeyboardButton(text=f"{month_names[month-1]} {year}", callback_data="cal:ignore"))
    
    # Кнопка "следующий месяц"
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"cal:{next_year}-{next_month:02d}"))
    
    buttons.append(nav_row)
    
    # Дни недели
    buttons.append([
        InlineKeyboardButton(text="Пн", callback_data="cal:ignore"),
        InlineKeyboardButton(text="Вт", callback_data="cal:ignore"),
        InlineKeyboardButton(text="Ср", callback_data="cal:ignore"),
        InlineKeyboardButton(text="Чт", callback_data="cal:ignore"),
        InlineKeyboardButton(text="Пт", callback_data="cal:ignore"),
        InlineKeyboardButton(text="Сб", callback_data="cal:ignore"),
        InlineKeyboardButton(text="Вс", callback_data="cal:ignore")
    ])
    
    # Получаем календарь месяца
    cal = calendar.monthcalendar(year, month)
    
    for week in cal:
        week_buttons = []
        for day in week:
            if day == 0:
                # Пустая ячейка
                week_buttons.append(InlineKeyboardButton(text=" ", callback_data="cal:ignore"))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                date_obj = datetime(year, month, day)
                
                # Проверяем, доступна ли дата
                if date_obj < min_datetime:
                    # Дата в прошлом или недоступна
                    week_buttons.append(InlineKeyboardButton(text="·", callback_data="cal:ignore"))
                else:
                    # Доступная дата
                    week_buttons.append(InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"date:{date_str}"
                    ))
        
        buttons.append(week_buttons)
    
    # Кнопка назад
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_island_name_ru(island_code: str) -> str:
    """Преобразование кода острова в русское название"""
    islands = {
        "boracay": "Боракай",
        "cebu": "Себу",
        "manila": "Манила",
        "bohol": "Бохоль",
        "palawan": "Палаван",
        "other": "Другие острова"
    }
    return islands.get(island_code, island_code)


# Кеш для курсов валют
_exchange_rates_cache = None
_cache_timestamp = None


def get_exchange_rates() -> dict:
    """
    Получение актуальных курсов валют из API с кешированием
    Использует exchangerate-api.com (бесплатный, без регистрации)
    Кеширование на 1 час
    """
    global _exchange_rates_cache, _cache_timestamp

    # Проверяем кеш (обновляем раз в час)
    if _exchange_rates_cache and _cache_timestamp:
        if datetime.now() - _cache_timestamp < timedelta(hours=1):
            return _exchange_rates_cache

    # Fallback курсы на случай ошибки API
    fallback_rates = {
        "usd": 1.0,
        "rub": 80.0,
        "peso": 56.0
    }

    try:
        # Используем бесплатный API exchangerate-api.com
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        if response.status_code == 200:
            data = response.json()
            rates = data.get("rates", {})
            _exchange_rates_cache = {
                "usd": 1.0,
                "rub": rates.get("RUB", 80.0),
                "peso": rates.get("PHP", 56.0)  # PHP = Philippine Peso
            }
            _cache_timestamp = datetime.now()
            return _exchange_rates_cache
    except:
        pass

    # Возвращаем fallback
    _exchange_rates_cache = fallback_rates
    _cache_timestamp = datetime.now()
    return fallback_rates


def convert_price(amount: float, from_currency: str, to_currency: str) -> float:
    """Конвертация валюты с актуальными курсами"""
    rates = get_exchange_rates()

    # Конвертируем в USD, затем в целевую валюту
    usd_amount = amount / rates[from_currency]
    result = usd_amount * rates[to_currency]

    return round(result, 2)


def get_currency_symbol(currency: str) -> str:
    """Получить символ валюты"""
    symbols = {
        "usd": "$",
        "rub": "₽",
        "peso": "₱"
    }
    return symbols.get(currency, "$")


def validate_phone_number(text: str) -> tuple[bool, str]:
    """
    Валидация номера телефона
    Возвращает: (валидно, очищенный_номер)
    
    Принимает форматы:
    - +79991234567
    - 89991234567
    - 9991234567
    - +7 (999) 123-45-67
    - и другие с пробелами, скобками, дефисами
    """
    # Убираем все символы кроме цифр и +
    cleaned = re.sub(r'[^\d+]', '', text.strip())
    
    # Проверяем минимальную длину (хотя бы 10 цифр)
    digits_only = re.sub(r'[^\d]', '', cleaned)
    
    if len(digits_only) < 10:
        return False, ""
    
    # Если номер начинается с 8, заменяем на +7
    if cleaned.startswith('8') and len(digits_only) == 11:
        cleaned = '+7' + cleaned[1:]
    
    # Если номер не начинается с +, добавляем +
    if not cleaned.startswith('+'):
        # Если 11 цифр и начинается с 7, добавляем +
        if len(digits_only) == 11 and digits_only[0] == '7':
            cleaned = '+' + cleaned
        # Если 10 цифр (без кода страны), добавляем +7
        elif len(digits_only) == 10:
            cleaned = '+7' + cleaned
        else:
            cleaned = '+' + cleaned
    
    return True, cleaned


async def send_items_page(
    message,
    items: list,
    page: int,
    per_page: int,
    format_card_func,
    get_keyboard_func,
    get_photo_func,
    callback_prefix: str,
    page_title: str = "Страница",
    parse_mode: str = None,
    page_1_based: bool = False
):
    """
    Универсальная функция для постраничного вывода элементов

    Args:
        message: Message объект для отправки
        items: Список элементов для отображения
        page: Номер текущей страницы (0-based или 1-based в зависимости от page_1_based)
        per_page: Количество элементов на странице
        format_card_func: Функция форматирования карточки (item) -> str
        get_keyboard_func: Функция создания клавиатуры для карточки (item) -> InlineKeyboardMarkup
        get_photo_func: Async функция получения фото (item) -> photo или None
        callback_prefix: Префикс для callback пагинации (например, "pkg_cards_page")
        page_title: Название в контрольном сообщении (по умолчанию "Страница")
        parse_mode: Режим парсинга (None, "Markdown", "HTML")
        page_1_based: Если True, page интерпретируется как 1-based (по умолчанию False - 0-based)
    """
    import math
    import asyncio

    if not items:
        return

    # Конвертируем в 0-based индекс для внутренней логики
    if page_1_based:
        page = page - 1

    total_pages = math.ceil(len(items) / per_page)

    # Проверяем границы
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1

    # Получаем элементы для текущей страницы
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(items))
    page_items = items[start_idx:end_idx]

    # Отправляем карточки
    for item in page_items:
        card_text = format_card_func(item)
        keyboard = get_keyboard_func(item)

        # Получаем фото если есть
        photo = await get_photo_func(item) if get_photo_func else None

        kwargs = {"reply_markup": keyboard}
        if parse_mode:
            kwargs["parse_mode"] = parse_mode

        try:
            if photo:
                await message.answer_photo(
                    photo=photo,
                    caption=card_text,
                    **kwargs
                )
            else:
                await message.answer(
                    card_text,
                    **kwargs
                )
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"Ошибка при отправке карточки: {e}")
            continue

    # Формируем клавиатуру с пагинацией
    nav_buttons = []

    # Определяем значения для callback (0-based или 1-based)
    callback_offset = 1 if page_1_based else 0

    # Кнопка "Назад"
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"{callback_prefix}:{page + callback_offset - 1}"
        ))

    # Кнопки страниц
    page_buttons = []
    start_page = max(0, page - 2)
    end_page = min(total_pages, start_page + 5)

    for p in range(start_page, end_page):
        display_num = p + 1
        callback_num = p + callback_offset
        if p == page:
            page_buttons.append(InlineKeyboardButton(
                text=f"• {display_num} •",
                callback_data=f"{callback_prefix}:{callback_num}"
            ))
        else:
            page_buttons.append(InlineKeyboardButton(
                text=str(display_num),
                callback_data=f"{callback_prefix}:{callback_num}"
            ))

    # Кнопка "Вперед"
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"{callback_prefix}:{page + callback_offset + 1}"
        ))

    # Формируем итоговую клавиатуру
    control_buttons = []
    if nav_buttons:
        control_buttons.append(nav_buttons)
    if page_buttons:
        control_buttons.append(page_buttons)

    control_buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")])

    control_keyboard = InlineKeyboardMarkup(inline_keyboard=control_buttons)

    control_kwargs = {"reply_markup": control_keyboard}
    if parse_mode:
        control_kwargs["parse_mode"] = parse_mode

    await message.answer(
        f"📋 {page_title} {page+1} из {total_pages}",
        **control_kwargs
    )


async def show_loading_message(message: Message, text: str = "⏳ Загружаю актуальную информацию...") -> Message:
    """
    Показать сообщение о загрузке данных

    Args:
        message: Message объект
        text: Текст сообщения (по умолчанию с эмодзи загрузки)

    Returns:
        Message объект отправленного сообщения (для последующего удаления)
    """
    return await message.answer(text)


async def delete_loading_message(loading_msg: Message):
    """
    Удалить сообщение о загрузке

    Args:
        loading_msg: Message объект для удаления
    """
    try:
        await loading_msg.delete()
    except Exception:
        pass  # Игнорируем ошибки удаления