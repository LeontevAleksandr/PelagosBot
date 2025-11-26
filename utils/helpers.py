"""Вспомогательные функции"""
import re
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def validate_price_range(text: str) -> tuple[bool, int, int]:
    """
    Валидация формата диапазона цен (50-1000)
    Возвращает: (валидно, min_price, max_price)
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
    
    if min_price < 50 or max_price > 1000:
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


def convert_price(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Конвертация валюты (упрощенная версия)
    В реальной версии нужно использовать актуальные курсы
    """
    # Курсы относительно USD
    rates = {
        "usd": 1.0,
        "rub": 78.9,
        "peso": 58.8
    }
    
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