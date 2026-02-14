"""Обработчики поиска"""
import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import COMPANY_LINKS

from keyboards import (
    get_back_to_main_keyboard,
    get_search_category_keyboard,
    get_hotel_card_simple_keyboard,
    get_transfer_card_simple_keyboard
)
from states.user_states import UserStates
from utils.search_utils import hybrid_search
from utils.data_loader import get_data_loader
from utils.helpers import get_island_name_ru
from services.pelagos_api import PelagosAPI

logger = logging.getLogger(__name__)

router = Router()


# ========== Старт поиска ==========

@router.message(F.text == "🔍 Поиск")
async def show_search(message: Message, state: FSMContext):
    """Показать выбор категории для поиска"""
    # Очищаем любое предыдущее состояние (например, HOTELS_INPUT_ROOM_COUNT)
    await state.clear()

    text = (
        "🔍 <b>Поиск по системе</b>\n\n"
        "Выберите категорию для поиска:"
    )

    await message.answer(
        text,
        reply_markup=get_search_category_keyboard()
    )
    await state.set_state(UserStates.SEARCH_SELECT_CATEGORY)


# ========== Выбор категории ==========

@router.callback_query(F.data == "search:back")
async def back_to_search_categories(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору категорий поиска"""
    await callback.answer()

    text = (
        "🔍 <b>Поиск по системе</b>\n\n"
        "Выберите категорию для поиска:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_search_category_keyboard()
    )
    await state.set_state(UserStates.SEARCH_SELECT_CATEGORY)


@router.callback_query(F.data.startswith("search:"), UserStates.SEARCH_SELECT_CATEGORY)
async def select_search_category(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории поиска"""
    await callback.answer()

    category = callback.data.split(":")[1]

    # Обработка кнопки "назад"
    if category == "back":
        return

    # Сохраняем категорию
    await state.update_data(search_category=category)

    # Для пакетных туров - показываем заглушку
    if category == "packages":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Посетить сайт", url=COMPANY_LINKS["packages"])],
            [InlineKeyboardButton(text="💬 Связаться с менеджером", url=COMPANY_LINKS["support"])],
            [InlineKeyboardButton(text="🔍 Вернуться к поиску", callback_data="search:back")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
        ])

        text = (
            "📦 <b>Поиск пакетных туров</b>\n\n"
            "Раздел с пакетными турами находится в разработке!\n\n"
            "🌟 Чтобы ознакомиться с актуальными предложениями по пакетным турам, "
            "пожалуйста, посетите наш сайт или свяжитесь с менеджером.\n\n"
            "Мы работаем над тем, чтобы скоро вы могли искать туры прямо в боте! 🚀"
        )

        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
        return

    # Для экскурсий - сначала выбор типа
    if category == "excursions":
        from keyboards.excursions import get_excursion_type_keyboard

        text = (
            "🔍 <b>Поиск экскурсий</b>\n\n"
            "Какой тип экскурсий вы хотите найти?"
        )

        await callback.message.edit_text(
            text,
            reply_markup=get_excursion_type_keyboard()
        )

        await state.set_state(UserStates.SEARCH_EXCURSIONS_SELECT_TYPE)
        return

    # Для отелей и трансферов - сразу ввод запроса
    category_names = {
        "hotels": "отелей",
        "transfers": "трансферов"
    }

    category_name = category_names.get(category, "")

    text = (
        f"🔍 <b>Поиск {category_name}</b>\n\n"
        f"Введите название или ключевые слова для поиска.\n\n"
        f"<i>Например: \"Shangri-La\", \"пляж\", \"романтик\" и т.д.</i>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_main_keyboard()
    )

    await state.set_state(UserStates.SEARCH_INPUT_QUERY)


# ========== Выбор типа экскурсии ==========

@router.callback_query(F.data.startswith("exc_type:"), UserStates.SEARCH_EXCURSIONS_SELECT_TYPE)
async def select_excursion_type_for_search(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа экскурсии для поиска"""
    await callback.answer()

    excursion_type = callback.data.split(":")[1]

    # Сохраняем тип экскурсии
    await state.update_data(search_excursion_type=excursion_type)

    # Названия типов для отображения
    type_names = {
        "group": "групповых экскурсий",
        "private": "индивидуальных экскурсий",
        "companions": "экскурсий с поиском попутчиков"
    }

    type_name = type_names.get(excursion_type, "экскурсий")

    text = (
        f"🔍 <b>Поиск {type_name}</b>\n\n"
        f"Введите название или ключевые слова для поиска.\n\n"
        f"<i>Например: \"дайвинг\", \"водопад\", \"city tour\" и т.д.</i>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_main_keyboard()
    )

    await state.set_state(UserStates.SEARCH_INPUT_QUERY)


# ========== Ввод запроса и выполнение поиска ==========

@router.message(F.text, UserStates.SEARCH_INPUT_QUERY)
async def process_search_query(message: Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = message.text.strip()

    if not query or len(query) < 2:
        await message.answer(
            "⚠️ Запрос слишком короткий. Введите минимум 2 символа.",
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Показываем индикатор загрузки
    loading_msg = await message.answer("🔍 Ищу...")

    try:
        # Получаем данные из состояния
        data = await state.get_data()
        category = data.get("search_category")

        # Выполняем поиск в зависимости от категории
        if category == "hotels":
            results = await search_hotels(query)
            await display_hotel_results(message, query, results, state)
        elif category == "excursions":
            excursion_type = data.get("search_excursion_type", "private")
            results = await search_excursions(query, excursion_type)
            await display_excursion_results(message, query, results, state)
        elif category == "transfers":
            results = await search_transfers(query)
            await display_transfer_results(message, query, results, state)
            await state.set_state(UserStates.SEARCH_SHOW_RESULTS)
        else:
            await message.answer(
                "❌ Неизвестная категория поиска",
                reply_markup=get_back_to_main_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при поиске. Попробуйте еще раз.",
            reply_markup=get_back_to_main_keyboard()
        )
    finally:
        # Удаляем сообщение о загрузке
        try:
            await loading_msg.delete()
        except:
            pass


# ========== Поиск по категориям ==========

async def search_hotels(query: str) -> list:
    """Поиск отелей"""
    try:
        # Используем API напрямую для поиска отелей
        api = PelagosAPI(api_key=os.getenv("PELAGOS_API_KEY"))

        # Собираем отели со всех островов
        all_hotels = []
        locations = ["cebu", "boracay", "bohol", "palawan", "manila-luson"]

        for location in locations:
            # Получаем все отели локации
            hotels = await api.get_all_hotels(location)

            # Конвертируем объекты Hotel в словари и добавляем location_code
            for hotel in hotels:
                hotel_dict = {
                    'id': str(hotel.id),
                    'name': hotel.name,
                    'stars': hotel.stars if hasattr(hotel, 'stars') else 0,
                    'address': hotel.address if hasattr(hotel, 'address') else '',
                    'location': hotel.location if hasattr(hotel, 'location') else 0,
                    'location_code': location,
                    'island_name': get_island_name_ru(location),  # Добавляем имя острова на русском
                    'room_type': 'Все типы номеров',  # Для поиска показываем общий текст
                    'photo': None,  # Будет заполнено позже если нужно
                    'pics': hotel.pics if hasattr(hotel, 'pics') else []
                }

                # Получаем URL первого фото если есть
                if hotel_dict['pics'] and len(hotel_dict['pics']) > 0:
                    pic = hotel_dict['pics'][0]
                    if isinstance(pic, dict):
                        md5 = pic.get('md5', '')
                        filename = pic.get('filename', '')
                        if md5 and filename:
                            hotel_dict['photo'] = f"https://app.pelagos.ru/pic/{md5}/{filename}"

                all_hotels.append(hotel_dict)

        await api.close()

        # Выполняем умный поиск с синонимами
        results = hybrid_search(
            query=query,
            items=all_hotels,
            field_name="name",
            limit=15,  # Увеличили лимит
            threshold=40  # Снизили порог для большей гибкости
        )

        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске отелей: {e}", exc_info=True)
        return []


async def search_excursions(query: str, excursion_type: str = "private") -> list:
    """Поиск экскурсий по ключевым словам

    Args:
        query: поисковый запрос
        excursion_type: тип экскурсии (group, private, companions)
    """
    try:
        # Используем DataLoader для получения экскурсий
        loader = get_data_loader()

        # Для индивидуальных экскурсий используем get_private_excursions
        if excursion_type == "private":
            api = PelagosAPI(api_key=os.getenv("PELAGOS_API_KEY"))

            # Получаем индивидуальные экскурсии со ВСЕХ островов одним запросом
            from datetime import datetime, timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            api_date = tomorrow.strftime("%d.%m.%Y")

            # location_id=0 означает ВСЕ острова (включая Манилу, Корон, Минданао и др.)
            all_services = await api.get_private_excursions(
                location_id=0,
                date=api_date
            )

            excursions = all_services
            await api.close()

        # Для групповых и попутчиков - получаем через загрузчик
        elif excursion_type in ["group", "companions"]:
            # Получаем экскурсии island=None означает загрузку всех доступных островов
            excursions = await loader.get_excursions_by_filters(
                island=None,
                excursion_type=excursion_type
            )
        else:
            return []

        # Выполняем умный поиск с синонимами
        results = hybrid_search(
            query=query,
            items=excursions,
            field_name="name",
            limit=15,  # Увеличили лимит
            threshold=40  # Снизили порог для большей гибкости
        )

        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске экскурсий: {e}", exc_info=True)
        return []


async def search_transfers(query: str) -> list:
    """Поиск трансферов"""
    try:
        # Используем API для поиска трансферов
        api = PelagosAPI(api_key=os.getenv("PELAGOS_API_KEY"))

        # Получаем все трансферы
        all_transfers = await api.get_all_transfers()

        # Выполняем нечеткий поиск
        results = hybrid_search(
            query=query,
            items=all_transfers,
            field_name="name",
            limit=10,
            threshold=50
        )

        await api.close()
        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске трансферов: {e}", exc_info=True)
        return []


# ========== Отображение результатов ==========

async def display_hotel_results(message: Message, query: str, results: list, state: FSMContext):
    """Отображение результатов поиска отелей - переброс на флоу отелей"""
    if not results:
        text = f"🔍 По запросу <b>'{query}'</b> ничего не найдено.\n\nПопробуйте изменить запрос."
        await message.answer(
            text,
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Импортируем необходимые функции
    from datetime import datetime, timedelta
    from handlers.hotels import send_hotels_cards_page

    # Получаем отели из результатов (убираем score)
    hotels = [hotel for hotel, score in results]

    # Устанавливаем дефолтные даты если их нет
    data = await state.get_data()
    check_in = data.get('check_in')
    check_out = data.get('check_out')

    if not check_in:
        # Завтра
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if not check_out:
        # Послезавтра
        check_out = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

    # Устанавливаем данные для флоу отелей
    await state.update_data(
        search_island=None,  # None означает что используем filtered_hotels
        search_query=query,  # Сохраняем поисковый запрос
        filtered_hotels=hotels,  # Сохраняем отфильтрованные отели
        stars=None,
        min_price=None,
        max_price=None,
        check_in=check_in,
        check_out=check_out
    )

    # Переводим в состояние просмотра результатов
    await state.set_state(UserStates.HOTELS_SHOW_RESULTS)

    # Показываем информационное сообщение
    info_text = (
        f"🔍 <b>Найдено {len(results)} отел(я/ей)</b> по запросу <b>\"{query}\"</b>\n\n"
        f"Загружаю результаты..."
    )
    await message.answer(info_text)

    # Используем существующую функцию для отображения первой страницы
    await send_hotels_cards_page(message, state, page=1)


async def display_excursion_results(message: Message, query: str, results: list, state: FSMContext):
    """Отображение результатов поиска экскурсий - переброс на флоу экскурсий"""
    if not results:
        text = f"🔍 По запросу <b>'{query}'</b> ничего не найдено.\n\nПопробуйте изменить запрос."
        await message.answer(
            text,
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Получаем данные из состояния
    data = await state.get_data()
    excursion_type = data.get("search_excursion_type", "private")

    # Получаем экскурсии из результатов (убираем score)
    excursions = [excursion for excursion, score in results]

    # Для индивидуальных экскурсий используем существующий флоу
    if excursion_type == "private":
        # Импортируем необходимые функции
        from utils.loaders.excursions.transformers import ServiceTransformer

        # Преобразуем словари в формат для обработчика
        # get_private_excursions уже возвращает словари, просто передаем их в _service_to_dict
        excursions_dict = []
        for exc in excursions:
            # exc уже словарь из get_private_excursions, передаем напрямую
            exc_dict = ServiceTransformer.transform(exc, excursion_type="private")
            if exc_dict:
                excursions_dict.append(exc_dict)

        # Сохраняем найденные экскурсии
        await state.update_data(
            search_query=query,
            filtered_excursions=excursions_dict,
            excursions=excursions_dict,
            excursion_type=excursion_type
        )

        # Показываем информационное сообщение
        info_text = f"🔍 <b>Найдено {len(results)} экскурси(й/и)</b> по запросу <b>\"{query}\"</b>\n\n"
        await message.answer(info_text)

        # ИСПРАВЛЕНИЕ: Запрашиваем количество человек (как в обычном флоу)
        from handlers.excursions.common import get_people_count_keyboard
        from utils.texts import EXCURSIONS_PRIVATE_INTRO

        await message.answer(
            EXCURSIONS_PRIVATE_INTRO,
            reply_markup=get_people_count_keyboard()
        )
        await state.set_state(UserStates.SEARCH_PRIVATE_INPUT_PEOPLE)

    # Для групповых и попутчиков экскурсии уже в формате dict
    elif excursion_type in ["group", "companions"]:
        # ИСПРАВЛЕНИЕ: Дозагружаем цены для групповых экскурсий
        if excursion_type == "group":
            logger.info(f"📊 Дозагрузка цен для {len(excursions)} найденных групповых экскурсий...")
            loader = get_data_loader()
            for excursion in excursions:
                if not excursion.get('price_usd') or excursion.get('price_usd') == 0:
                    full_excursion = await loader.get_excursion_by_id(excursion['id'])
                    if full_excursion and full_excursion.get('price_usd'):
                        excursion['price'] = full_excursion['price_usd']
                        excursion['price_usd'] = full_excursion['price_usd']
                        logger.info(f"   ✓ {excursion['name']}: ${full_excursion['price_usd']} за чел")

        # Сохраняем найденные экскурсии
        await state.update_data(
            search_query=query,
            filtered_excursions=excursions,
            excursions=excursions,
            current_excursion_index=0,
            excursion_type=excursion_type
        )

        # Показываем информационное сообщение
        info_text = f"🔍 <b>Найдено {len(results)} экскурси(й/и)</b> по запросу <b>\"{query}\"</b>\n\n"
        await message.answer(info_text)

        # Для групповых экскурсий устанавливаем количество людей = 1 по умолчанию
        if excursion_type == "group":
            from handlers.excursions.group import show_group_excursion

            # Устанавливаем количество людей = 1 (пользователь может изменить позже)
            await state.update_data(excursion_people_count=1)
            await state.set_state(UserStates.EXCURSIONS_SHOW_RESULTS)
            await show_group_excursion(message, state, 0)
        else:
            # Для попутчиков показываем сразу
            from handlers.excursions.group import show_group_excursion
            await state.set_state(UserStates.EXCURSIONS_SHOW_RESULTS)
            await show_group_excursion(message, state, 0)

    # Неизвестный тип
    else:
        text = "❌ Неизвестный тип экскурсии"
        await message.answer(
            text,
            reply_markup=get_back_to_main_keyboard()
        )
        await state.set_state(UserStates.SEARCH_SHOW_RESULTS)


async def display_transfer_results(message: Message, query: str, results: list, state: FSMContext):
    """Отображение результатов поиска трансферов"""
    if not results:
        text = f"🔍 По запросу <b>'{query}'</b> ничего не найдено.\n\nПопробуйте изменить запрос."
        await message.answer(
            text,
            reply_markup=get_back_to_main_keyboard()
        )
        return

    # Формируем текст с результатами
    text = f"🔍 <b>Результаты поиска трансферов</b>\n\n"
    text += f"Найдено <b>{len(results)}</b> трансфер(а/ов) по запросу <b>'{query}'</b>:\n\n"

    for i, (transfer, score) in enumerate(results[:5], 1):
        # Получаем локацию
        location_id = transfer.location if hasattr(transfer, 'location') else 0
        location_names = {9: "Себу", 10: "Бохол", 8: "Боракай", 0: "Общие"}
        location_name = location_names.get(location_id, "Неизвестно")

        text += f"{i}. <b>{transfer.name}</b>\n"
        text += f"   📍 {location_name}\n"

        # Показываем процент совпадения
        if score < 100:
            text += f"   🎯 Совпадение: {int(score)}%\n"

        text += "\n"

    if len(results) > 5:
        text += f"<i>И еще {len(results) - 5} результат(ов)...</i>\n\n"

    text += "Используйте раздел 🚗 <b>Трансферы</b> для полного флоу бронирования."

    await message.answer(
        text,
        reply_markup=get_back_to_main_keyboard()
    )
