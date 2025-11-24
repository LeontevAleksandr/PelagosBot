"""
CRUD операции для работы с базой данных.
Пока что заглушки - будут реализованы позже.
"""


# Отели
async def get_hotel_photo_from_db(hotel_id: int):
    """Получить фото отеля"""
    pass


async def search(query: str):
    """Поиск по базе данных"""
    pass


async def get_hotel_name_by_key(hotel_key: str):
    """Получить название отеля по ключу"""
    pass


# Услуги
async def get_service_name_by_id(service_id: int):
    """Получить название услуги по ID"""
    pass


async def get_service_by_guest_count(guest_count: int):
    """Получить услуги по количеству гостей"""
    pass


# Экскурсии
async def get_excursions_by_island(island: str):
    """Получить экскурсии по острову"""
    pass


async def search_excursions(query: str):
    """Поиск экскурсий"""
    pass


async def get_excursions_paginated(offset: int, limit: int):
    """Получить экскурсии с пагинацией"""
    pass


async def get_excursions_by_id(excursion_id: int):
    """Получить экскурсию по ID"""
    pass


# Комнаты
async def get_filtered_rooms_by_guests_number(guest_count: int):
    """Получить комнаты по количеству гостей"""
    pass


# Заказы
async def insert_into_orders_table(order_data: dict):
    """Добавить заказ в таблицу"""
    pass


async def delete_orders_for_user(user_id: int):
    """Удалить заказы пользователя"""
    pass


async def get_orders_for_user(user_id: int):
    """Получить заказы пользователя"""
    # Временная заглушка
    return []