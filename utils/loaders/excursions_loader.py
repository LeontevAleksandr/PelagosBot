"""Загрузчик данных для экскурсий"""
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ExcursionsLoader:
    """Класс для работы с экскурсиями (из JSON)"""

    def __init__(self, json_path: str = "data/mock_data.json"):
        self.json_path = json_path
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Загрузить данные из JSON"""
        if not os.path.exists(self.json_path):
            return {
                "excursions": [],
                "users": {},
                "orders": []
            }

        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_excursions_by_filters(
        self,
        island: str = None,
        excursion_type: str = None,
        date: str = None
    ) -> list:
        """
        Получить экскурсии по фильтрам

        Args:
            island: код острова
            excursion_type: тип экскурсии (group, private, companions)
            date: дата в формате YYYY-MM-DD (для групповых и companions)
        """
        excursions = self.data.get("excursions", [])

        # Фильтр по острову
        if island:
            excursions = [e for e in excursions if e["island"] == island]

        # Фильтр по типу
        if excursion_type:
            excursions = [e for e in excursions if e["type"] == excursion_type]

        # Фильтр по дате (для групповых и companions)
        if date:
            excursions = [e for e in excursions if e.get("date") == date]

        return excursions

    def get_excursion_by_id(self, excursion_id: str) -> dict:
        """Получить экскурсию по ID"""
        excursions = self.data.get("excursions", [])
        for excursion in excursions:
            if excursion["id"] == excursion_id:
                return excursion
        return None

    def get_companions_by_month(self, island: str, year: int, month: int) -> list:
        """Получить экскурсии с поиском попутчиков за месяц"""
        excursions = self.get_excursions_by_filters(island=island, excursion_type="companions")

        # Фильтруем по месяцу
        result = []
        for exc in excursions:
            if exc.get("date"):
                try:
                    exc_date = datetime.strptime(exc["date"], "%Y-%m-%d")
                    if exc_date.year == year and exc_date.month == month:
                        result.append(exc)
                except:
                    pass

        return result
