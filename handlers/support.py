"""Обработчики поддержки"""
from aiogram import Router, F
from aiogram.types import Message

from keyboards import get_support_keyboard
from utils.texts import SUPPORT_TEXT

router = Router()


@router.message(F.text == "💬 Поддержка")
async def show_support(message: Message):
    """Показать контакты поддержки"""
    await message.answer(
        SUPPORT_TEXT,
        reply_markup=get_support_keyboard()
    )