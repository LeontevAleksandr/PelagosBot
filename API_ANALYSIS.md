# Анализ работы с Pelagos API

## Обзор структуры

### 1. API Client ([services/api_client.py](services/api_client.py))
Базовый HTTP клиент для работы с API:
- Использует `aiohttp` для асинхронных запросов
- Автоматически добавляет заголовок `X-Key` с API ключом
- Обрабатывает ошибки и таймауты
- Поддерживает GET и POST запросы

### 2. Pelagos API Service ([services/pelagos_api.py](services/pelagos_api.py))
Сервис-обертка над API клиентом:
- Реализует методы для работы с регионами, отелями, номерами, услугами
- Автоматическая пагинация для получения всех данных
- Методы поиска по отелям и услугам
- Преобразует JSON ответы в типизированные объекты

### 3. Схемы данных ([services/schemas.py](services/schemas.py))
Модели данных с методами `from_dict()`:
- `Region` - регионы и локации
- `Hotel` - отели
- `HotelRoom` - номера в отелях
- `Service` - услуги (экскурсии, трансферы)
- `RoomPrices` - цены на номера
- `Pagination` - информация о пагинации

## Примеры использования API

### Базовая инициализация
```python
from services.pelagos_api import PelagosAPI

api = PelagosAPI(api_key='ваш_ключ_api')
```

### Получение регионов
```python
# Все регионы
regions = await api.get_regions()

# Только корневые регионы (без родителей)
root_regions = await api.get_root_regions()

# Поиск региона по коду
region = await api.get_region_by_code('cebu')
```

### Работа с отелями
```python
# Получить отели региона с пагинацией
result = await api.get_hotels('cebu', perpage=20, start=0)
hotels = result['hotels']
pagination = result['pagination']

# Получить ВСЕ отели региона (автоматическая пагинация)
all_hotels = await api.get_all_hotels('cebu')

# Поиск отелей по названию
hotels = await api.search_hotels('Shangri-La', limit=10)
```

### Работа с номерами
```python
# Номера отеля с пагинацией
result = await api.get_rooms(hotel_id=240, perpage=20)
rooms = result['rooms']

# Все номера отеля
all_rooms = await api.get_all_rooms(hotel_id=240)

# Цены на номер
prices = await api.get_room_prices(room_id=717)
```

### Работа с услугами
```python
# Получить услуги с пагинацией
result = await api.get_services(perpage=20, start=0)
services = result['services']

# Все услуги
all_services = await api.get_all_services()

# Поиск услуг
services = await api.search_services('экскурсия', limit=10)
```

## Важные особенности API

### 1. Структура регионов
- Регионы выстроены в иерархическую структуру
- Есть корневые регионы (parent = 0 или None)
- Есть дочерние регионы (parent != 0)
- **ВАЖНО**: Запросы отелей работают только для дочерних регионов!
  - `cebu`, `manila-luson`, `boracay` - работают ✓
  - `general` - не работает ✗

### 2. Эндпоинты API
```
GET /export-locations/                          - Список регионов
GET /export-hotels/{location_code}/             - Отели региона
GET /export-hotels-rooms/{hotel_id}/            - Номера отеля
GET /export-hotels-rooms-prices/{room_id}/      - Цены на номер
GET /export-services/                            - Услуги
GET /export-hotel/{hotel_id}/                   - Детальная информация об отеле
GET /export-services-xml/?cache=1               - XML с услугами
GET /export-rooms-xml/?cache=1                  - XML с номерами
GET /group-tours/{date}/?list=1&location={id}   - Индивидуальные экскурсии
GET /group-tours/{date}/flex/?calendar=1&location={id} - Поиск попутчиков (календарь)
GET /group-tours-event/{event_id}/?extend=1     - Детали события попутчика
```

### 3. Параметры пагинации
- `start` - начало (0 - первый элемент)
- `perpage` - количество элементов на странице
- Пагинация возвращается в поле `pages` ответа

### 4. Авторизация
Все запросы должны содержать заголовок:
```
X-Key: ваш_api_ключ
```

### 5. Формат ответа
```json
{
  "code": "OK",
  "locations": [...],  // или hotels, services, rooms
  "pages": {
    "total": 100,
    "perpage": 20,
    "start": 0
  }
}
```

При ошибке:
```json
{
  "code": "Error",
  "message": "текст ошибки"
}
```

## Работа с изображениями

API возвращает массив изображений в поле `pics`:
```python
{
  "id": 123,
  "md5": "abc123...",
  "filename": "hotel.jpg",
  "ext": "jpg",
  "size": 102400
}
```

### URL для получения изображений:
- Полное: `https://app.pelagos.ru/pic/{md5}/{filename}`
- Простой: `https://app.pelagos.ru/pic/{md5}/{md5}.{ext}`
- Миниатюра: `https://app.pelagos.ru/thumb/{md5}/{filename}`
- Произвольный размер: `https://app.pelagos.ru/freepic/{md5}/{filename}?opts=inner&size=300x200`

## Зависимости

```txt
aiohttp==3.9.1    - для асинхронных HTTP запросов
```

## Тестирование

Запуск тестов:
```bash
python te_api.py
```

Тесты проверяют:
1. Получение регионов
2. Получение корневых регионов
3. Получение отелей по региону
4. Получение услуг
5. Поиск отелей по названию

## Исправленные проблемы

1. **Отсутствие метода `from_dict()`** - добавлены classmethod для всех моделей
2. **Неправильная работа с корутинами** - исправлен срез `await func()[:2]` на правильный
3. **Запросы к корневым регионам** - поиск теперь использует дочерние регионы
4. **Отсутствие зависимости aiohttp** - добавлена в requirements.txt

## Рекомендации

1. Всегда закрывайте соединение после работы:
   ```python
   await api.close()
   ```

2. Используйте дочерние регионы для запросов отелей (cebu, boracay, manila-luson и т.д.)

3. Для больших объемов данных используйте методы `get_all_*` с автоматической пагинацией

4. Обрабатывайте случаи, когда API возвращает пустые списки или None

## Поиск попутчиков (Companions)

### Структура API для поиска попутчиков

Поиск попутчиков работает через flex API, который возвращает индивидуальные экскурсии с информацией о людях, ищущих попутчиков.

### Получение календаря попутчиков
```python
# Получить календарь с экскурсиями для поиска попутчиков
days = await api.get_companions_calendar(location_id=9, date="21.12.2025")

# Структура ответа:
# days = [
#   {
#     "dt": 1767369600,
#     "date": "03.01.2026",
#     "mon": 1,
#     "year": "2026",
#     "events": [
#       {
#         "id": 285,  # ID события (event_id)
#         "service_id": 18964,  # ID услуги
#         "pax": 2,  # Количество человек ищущих попутчиков
#         "service": {
#           "id": 18964,
#           "name": "Название экскурсии",
#           "location": 9,
#           "russian_guide": 10,
#           "pic": {...}
#         }
#       }
#     ]
#   }
# ]
```

### Получение деталей события попутчика
```python
# Получить детальную информацию о событии
event_details = await api.get_companion_event_details(event_id=285)

# Структура ответа включает:
# - Полную информацию о сервисе (service)
# - Список попутчиков (slst) с контактами
# - Цены для разного количества людей (rlst)
# - Фотографии (pics)
```

### Структура цен (rlst)

```python
# rlst содержит информацию о ценах для разного количества человек
"rlst": [
  {
    "clst": [
      {"grp": 1, "price": 365},  # Цена за человека для 1 чел.
      {"grp": 2, "price": 220},  # Цена за человека для 2 чел.
      {"grp": 3, "price": 195},  # Цена за человека для 3 чел.
      {"grp": 4, "price": 180},  # и т.д.
    ]
  }
]
```

### Структура списка попутчиков (slst)

```python
# slst содержит список людей, ищущих попутчиков
"slst": [
  {
    "id": 157,
    "title": "Анна",
    "pax": 2,  # Количество человек в группе
    "phone": "+7 950 209-02-91",
    "tg": ""
  }
]
```

### Важные отличия от групповых экскурсий

1. **ID**: Для попутчиков используется `event_id`, а не `service_id`
2. **Цены**: Цены зависят от количества человек и хранятся в `rlst.clst`
3. **Тип**: Это индивидуальные экскурсии, но с поиском попутчиков
4. **API endpoint**: Используется `/group-tours/{date}/flex/` с параметром `calendar=1`
