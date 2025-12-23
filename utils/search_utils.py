"""Утилиты для поиска с нечетким сопоставлением"""
from typing import List, Tuple, Any
from rapidfuzz import fuzz, process


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


def hybrid_search(
    query: str,
    items: List[Any],
    field_name: str = "name",
    limit: int = 10,
    threshold: int = 60
) -> List[Tuple[Any, float]]:
    """
    Гибридный поиск: сначала простой (быстрый), затем нечеткий (умный)

    Args:
        query: поисковый запрос
        items: список объектов для поиска
        field_name: имя поля для поиска
        limit: максимальное количество результатов
        threshold: минимальный процент совпадения для нечеткого поиска

    Returns:
        список кортежей (объект, процент_совпадения)
    """
    # Сначала пробуем простой поиск
    simple_results = simple_search(query, items, field_name)

    # Если нашли много точных совпадений, возвращаем их
    if len(simple_results) >= 3:
        # Добавляем оценку 100% для точных совпадений
        return [(item, 100.0) for item in simple_results[:limit]]

    # Иначе используем нечеткий поиск для большей гибкости
    fuzzy_results = fuzzy_search(query, items, field_name, limit, threshold)

    # Объединяем результаты, отдавая приоритет точным совпадениям
    seen_ids = set()
    combined = []

    # Сначала добавляем точные совпадения
    for item in simple_results:
        item_id = id(item)
        if item_id not in seen_ids:
            seen_ids.add(item_id)
            combined.append((item, 100.0))

    # Затем добавляем нечеткие совпадения
    for item, score in fuzzy_results:
        item_id = id(item)
        if item_id not in seen_ids:
            seen_ids.add(item_id)
            combined.append((item, score))

    return combined[:limit]
