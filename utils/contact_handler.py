"""Универсальный обработчик запроса контактов"""
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from keyboards import get_back_to_main_keyboard
from utils.helpers import validate_phone_number
from utils.texts import CONTACT_RECEIVED
from states.user_states import UserStates


class ContactHandler:
    """Класс для обработки запроса контактов"""

    @staticmethod
    def get_use_saved_phone_keyboard(phone: str) -> InlineKeyboardMarkup:
        """Клавиатура для использования сохраненного номера"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Использовать {phone}", callback_data="phone:use_saved")],
            [InlineKeyboardButton(text="✏️ Ввести другой номер", callback_data="phone:enter_new")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back:main")]
        ])
        return keyboard

    @staticmethod
    async def request_phone(message: Message, state: FSMContext, contact_text: str = None) -> bool:
        """
        Запрос номера телефона с проверкой сохраненного

        Args:
            message: Сообщение от пользователя
            state: Состояние FSM
            contact_text: Текст запроса контакта (если None, используется стандартный)

        Returns:
            bool: True если номер уже сохранен, False если нужно запросить новый
        """
        data = await state.get_data()
        saved_phone = data.get("user_phone")

        if saved_phone:
            # Номер уже сохранен, предлагаем использовать его
            await message.edit_text(
                f"У вас сохранен номер телефона: {saved_phone}\n\n"
                "Хотите использовать его для оформления заказа?",
                reply_markup=ContactHandler.get_use_saved_phone_keyboard(saved_phone)
            )
            return True
        else:
            # Номера нет, запрашиваем новый
            text = contact_text or "Для оформления заказа поделитесь своими контактными данными.\n\nНаш менеджер свяжется с вами для подтверждения."
            from keyboards.hotels import get_share_contact_keyboard
            await message.edit_text(
                text,
                reply_markup=get_share_contact_keyboard()
            )
            return False
    
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
        
        # Сохраняем номер (для текущей сессии и как постоянный профиль)
        await state.update_data(phone_number=phone_number, user_phone=phone_number)
        
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
        
        # Сохраняем номер (для текущей сессии и как постоянный профиль)
        await state.update_data(phone_number=phone_number, user_phone=phone_number)
        
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