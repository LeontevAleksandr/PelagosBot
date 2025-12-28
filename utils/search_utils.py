"""Утилиты для поиска с нечетким сопоставлением"""
from typing import List, Tuple, Any
from rapidfuzz import fuzz, process

# Словарь синонимов для улучшения поиска
SYNONYMS = {
    # Отели
    "люкс": ["luxury", "deluxe", "premium", "vip"],
    "бюджет": ["budget", "cheap", "эконом", "economy"],
    "пляж": ["beach", "море", "sea"],
    "город": ["city", "central", "центр"],
    "романтик": ["romantic", "honeymoon", "медовый месяц"],
    "семья": ["family", "kids", "дети"],
    "боракай": ["boracay", "боракай", "boracay island"],

    # Экскурсии
    "дайвинг": ["diving", "дайв", "dive", "snorkel", "снорклинг"],
    "водопад": ["waterfall", "falls", "каскад"],
    "остров": ["island", "айланд"],
    "сноркелинг": ["snorkeling", "маска", "snorkel"],
    "акула": ["shark", "whale shark", "китовая"],
    "черепаха": ["turtle", "тартл"],
    "каньонинг": ["canyoning", "canyon"],
    "вулкан": ["volcano", "volcanic"],
}

def expand_query(query: str) -> str:
    """Расширяет запрос синонимами для лучшего поиска"""
    query_lower = query.lower()
    expanded_terms = [query]

    # Добавляем синонимы
    for word, synonyms in SYNONYMS.items():
        if word in query_lower:
            expanded_terms.extend(synonyms)
        # Обратная проверка
        for synonym in synonyms:
            if synonym.lower() in query_lower and word not in expanded_terms:
                expanded_terms.append(word)

    return " ".join(expanded_terms)


def fuzzy_search(
    query: str,
    items: List[Any],
    field_name: str = "name",
    limit: int = 10,
    threshold: int = 60
) -> List[Tuple[Any, float]]:
    """
    Выполняет нечеткий поиск по списку объектов

    Args:
        query: поисковый запрос
        items: список объектов для поиска
        field_name: имя поля для поиска (по умолчанию "name")
        limit: максимальное количество результатов
        threshold: минимальный процент совпадения (0-100)

    Returns:
        список кортежей (объект, процент_совпадения), отсортированный по релевантности
    """
    if not query or not items:
        return []

    # Создаем словарь для быстрого доступа к объектам по тексту поля
    text_to_item = {}
    texts = []

    for item in items:
        # Получаем значение поля (поддерживаем как dict, так и объекты с атрибутами)
        if isinstance(item, dict):
            text = str(item.get(field_name, ""))
        else:
            text = str(getattr(item, field_name, ""))

        if text:
            texts.append(text)
            text_to_item[text] = item

    if not texts:
        return []

    # Выполняем нечеткий поиск используя алгоритм token_set_ratio
    # Он хорошо работает с частичными совпадениями и разным порядком слов
    results = process.extract(
        query,
        texts,
        scorer=fuzz.token_set_ratio,
        limit=limit
    )

    # Фильтруем результаты по порогу и преобразуем в нужный формат
    filtered_results = []
    for text, score, _ in results:
        if score >= threshold:
            item = text_to_item[text]
            filtered_results.append((item, score))

    return filtered_results


def simple_search(
    query: str,
    items: List[Any],
    field_name: str = "name"
) -> List[Any]:
    """
    Простой поиск по вхождению подстроки (без учета регистра)

    Args:
        query: поисковый запрос
        items: список объектов для поиска
        field_name: имя поля для поиска

    Returns:
        список найденных объектов
    """
    if not query or not items:
        return []

    query_lower = query.lower()
    results = []

    for item in items:
        # Получаем значение поля
        if isinstance(item, dict):
            text = str(item.get(field_name, ""))
        else:
            text = str(getattr(item, field_name, ""))

        if query_lower in text.lower():
            results.append(item)

    return results


def multi_field_search(
    query: str,
    items: List[Any],
    fields: List[str] = None,
    limit: int = 10,
    threshold: int = 60
) -> List[Tuple[Any, float]]:
    """
    Поиск по нескольким полям с весами

    Args:
        query: поисковый запрос
        items: список объектов для поиска
        fields: список полей для поиска (по умолчанию ["name", "description"])
        limit: максимальное количество результатов
        threshold: минимальный процент совпадения

    Returns:
        список кортежей (объект, процент_совпадения)
    """
    if fields is None:
        fields = ["name", "description"]

    if not query or not items:
        return []

    # Расширяем запрос синонимами
    expanded_query = expand_query(query)

    # Создаем словарь результатов: item_id -> (item, max_score)
    results_dict = {}

    # Ищем по каждому полю
    for field in fields:
        field_results = fuzzy_search(expanded_query, items, field, limit=limit * 2, threshold=threshold - 10)

        for item, score in field_results:
            item_id = id(item)
            # Берем максимальный score среди всех полей
            if item_id not in results_dict or score > results_dict[item_id][1]:
                results_dict[item_id] = (item, score)

    # Сортируем по релевантности
    sorted_results = sorted(results_dict.values(), key=lambda x: x[1], reverse=True)

    return sorted_results[:limit]


def hybrid_search(
    query: str,
    items: List[Any],
    field_name: str = "name",
    limit: int = 10,
    threshold: int = 60
) -> List[Tuple[Any, float]]:
    """
    Умный гибридный поиск с синонимами и несколькими полями

    Args:
        query: поисковый запрос
        items: список объектов для поиска
        field_name: основное имя поля для поиска
        limit: максимальное количество результатов
        threshold: минимальный процент совпадения для нечеткого поиска

    Returns:
        список кортежей (объект, процент_совпадения)
    """
    # Расширяем запрос синонимами
    expanded_query = expand_query(query)

    # Сначала пробуем простой поиск с оригинальным запросом
    simple_results = simple_search(query, items, field_name)

    # Если нашли точные совпадения, добавляем их с максимальным score
    seen_ids = set()
    combined = []

    for item in simple_results[:limit]:
        item_id = id(item)
        seen_ids.add(item_id)
        combined.append((item, 100.0))

    # Если нашли достаточно, возвращаем
    if len(combined) >= limit:
        return combined

    # Ищем по основному полю с расширенным запросом
    fuzzy_results = fuzzy_search(expanded_query, items, field_name, limit * 2, threshold)

    # Добавляем результаты нечеткого поиска
    for item, score in fuzzy_results:
        item_id = id(item)
        if item_id not in seen_ids:
            seen_ids.add(item_id)
            combined.append((item, score))

    # Если все еще мало результатов, попробуем поиск по описанию
    if len(combined) < limit and any(
        isinstance(item, dict) and 'description' in item or hasattr(item, 'description')
        for item in items[:1] if items
    ):
        desc_results = fuzzy_search(expanded_query, items, "description", limit * 2, threshold - 10)
        for item, score in desc_results:
            item_id = id(item)
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                # Понижаем score для совпадений по описанию
                combined.append((item, score * 0.8))

    # Сортируем по релевантности и ограничиваем
    combined.sort(key=lambda x: x[1], reverse=True)
    return combined[:limit]
