from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """Состояния пользователя в боте"""
    
    # Общие состояния
    START = State()
    ASK_NAME = State()
    MAIN_MENU = State()
    
    # Отели
    HOTELS_SELECT_ISLAND = State()
    HOTELS_SELECT_OTHER_LOCATION = State()
    HOTELS_SELECT_CRITERIA = State()
    HOTELS_SELECT_STARS = State()
    HOTELS_SELECT_CURRENCY = State()
    HOTELS_SELECT_PRICE_METHOD = State()
    HOTELS_INPUT_CUSTOM_RANGE = State()
    HOTELS_SELECT_PRICE_RANGE = State()
    HOTELS_SELECT_CHECK_IN = State()
    HOTELS_SELECT_CHECK_OUT = State()
    HOTELS_SHOW_RESULTS = State()
    HOTELS_SELECT_ROOM = State()
    HOTELS_INPUT_ROOM_COUNT = State()
    
    # Экскурсии
    EXCURSIONS_SELECT_ISLAND = State()
    EXCURSIONS_SELECT_OTHER_LOCATION = State()
    EXCURSIONS_SELECT_TYPE = State()
    EXCURSIONS_GROUP_SELECT_DATE = State()
    EXCURSIONS_PRIVATE_INPUT_PEOPLE = State()
    EXCURSIONS_PRIVATE_SELECT_DATE = State()
    EXCURSIONS_SHOW_RESULTS = State()
    
    # Поиск попутчиков (будут реализованы позже)
    COMPANIONS_VIEW_LIST = State()
    COMPANIONS_SELECT_MONTH = State()
    COMPANIONS_SELECT_EXCURSION = State()
    COMPANIONS_VIEW_DETAILS = State()
    COMPANIONS_CREATE_INFO = State()
    COMPANIONS_CREATE_SELECT_EXCURSION = State()
    COMPANIONS_CREATE_SELECT_DATE = State()
    COMPANIONS_CREATE_INPUT_PEOPLE = State()
    
    # Пакетные туры (будут реализованы позже)
    PACKAGE_TOURS_SELECT_DATE = State()
    
    # Трансферы (будут реализованы позже)
    TRANSFERS_SELECT_ISLAND = State()
    TRANSFERS_INPUT_PEOPLE = State()
    TRANSFERS_SHOW_RESULTS = State()
    
    # Прочее
    OTHER_MENU = State()
    SHARE_CONTACT = State()