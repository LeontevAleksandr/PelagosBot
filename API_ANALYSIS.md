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
GET /export-locations/                     - Список регионов
GET /export-hotels/{location_code}/        - Отели региона
GET /export-hotels-rooms/{hotel_id}/       - Номера отеля
GET /export-hotels-rooms-prices/{room_id}/ - Цены на номер
GET /export-services/                       - Услуги
GET /export-hotel/{hotel_id}/              - Детальная информация об отеле
GET /export-services-xml/?cache=1          - XML с услугами
GET /export-rooms-xml/?cache=1             - XML с номерами
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
