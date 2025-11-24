"""Обработчики поиска"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards import get_back_to_main_keyboard
from utils.texts import SEARCH_TEXT
from database.db_crud import search

router = Router()


@router.message(F.text == "🔍 Поиск")
async def show_search(message: Message):
    """Показать форму поиска"""
    await message.answer(
        SEARCH_TEXT,
        reply_markup=get_back_to_main_keyboard()
    )


@router.message(F.text)
async def process_search(message: Message):
    """
    Обработка поискового запроса
    Этот обработчик должен быть зарегистрирован последним,
    чтобы перехватывать все текстовые сообщения, не обработанные ранее
    """
    query = message.text.strip()
    
    # Выполняем поиск (пока заглушка)
    results = await search(query)
    
    if not results:
        text = f"🔍 По запросу '{query}' ничего не найдено.\n\nПопробуйте изменить запрос."
    else:
        text = f"🔍 Результаты поиска по запросу '{query}':\n\n"
        # TODO: Форматирование результатов поиска
        text += "Результаты будут отображаться здесь."
    
    await message.answer(
        text,
        reply_markup=get_back_to_main_keyboard()
    )