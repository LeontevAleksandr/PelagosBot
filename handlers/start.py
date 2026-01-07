"""Обработчики команды /start и знакомства с пользователем"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from states.user_states import UserStates
from keyboards import get_main_reply_keyboard, get_main_menu_keyboard
from utils.texts import GREETING, get_main_menu_text
from utils.version import format_version_message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Обработчик команды /start
    Приветствие и запрос имени
    """
    # Отправляем постоянную клавиатуру
    await message.answer(
        GREETING,
        reply_markup=get_main_reply_keyboard()
    )
    
    # Устанавливаем состояние ожидания имени
    await state.set_state(UserStates.ASK_NAME)


@router.message(UserStates.ASK_NAME, F.text)
async def process_name(message: Message, state: FSMContext):
    """
    Обработка ввода имени пользователя
    """
    user_name = message.text.strip()
    
    # Сохраняем имя в состоянии
    await state.update_data(user_name=user_name)
    
    # Показываем главное меню
    await message.answer(
        get_main_menu_text(user_name),
        reply_markup=get_main_menu_keyboard()
    )
    
    # Переходим в состояние главного меню
    await state.set_state(UserStates.MAIN_MENU)


@router.message(Command("head"))
async def cmd_head(message: Message):
    """
    Обработчик команды /head
    Показывает текущую версию бота (git hash)
    """
    await message.answer(format_version_message())