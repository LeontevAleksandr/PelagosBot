"""Универсальный обработчик запроса контактов"""
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards import get_back_to_main_keyboard
from utils.helpers import validate_phone_number
from utils.texts import CONTACT_RECEIVED
from states.user_states import UserStates


class ContactHandler:
    """Класс для обработки запроса контактов"""
    
    @staticmethod
    async def process_text_phone(message: Message, state: FSMContext) -> bool:
        """
        Обработка текстового ввода номера телефона
        
        Returns:
            bool: True если номер валиден и обработан, False если нет
        """
        valid, phone_number = validate_phone_number(message.text)
        
        if not valid:
            await message.answer(
                "❌ Неверный формат номера телефона.\n\nПожалуйста, введите номер в формате:\n+79991234567 или 89991234567",
                reply_markup=get_back_to_main_keyboard()
            )
            return False
        
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        # Сохраняем номер
        await state.update_data(phone_number=phone_number)
        
        # Отправляем подтверждение
        await message.answer(
            CONTACT_RECEIVED,
            reply_markup=get_back_to_main_keyboard()
        )
        
        # Возвращаемся в главное меню
        await state.set_state(UserStates.MAIN_MENU)
        
        return True
    
    @staticmethod
    async def process_contact(message: Message, state: FSMContext) -> bool:
        """
        Обработка контакта через кнопку Telegram
        
        Returns:
            bool: True если контакт обработан
        """
        phone_number = message.contact.phone_number
        
        # Добавляем + если его нет
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        # Сохраняем номер
        await state.update_data(phone_number=phone_number)
        
        # Отправляем подтверждение
        await message.answer(
            CONTACT_RECEIVED,
            reply_markup=get_back_to_main_keyboard()
        )
        
        # Возвращаемся в главное меню
        await state.set_state(UserStates.MAIN_MENU)
        
        return True


# Глобальный экземпляр
contact_handler = ContactHandler()