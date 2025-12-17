"""Загрузчик данных для пакетных туров"""
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PackagesLoader:
    """Класс для работы с пакетными турами (из JSON)"""

    def __init__(self, json_path: str = "data/mock_data.json"):
        self.json_path = json_path
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Загрузить данные из JSON"""
        if not os.path.exists(self.json_path):
            return {
                "packages": [],
                "users": {},
                "orders": []
            }

        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_packages_by_date(self, target_date: str = None) -> list:
        """
        Получить пакетные туры близкие к указанной дате

        Args:
            target_date: дата в формате YYYY-MM-DD (если None - все туры)
        """
        packages = self.data.get("packages", [])

        if not target_date:
            return packages

        # Ищем туры, которые начинаются в пределах ±30 дней от указанной даты
        target = datetime.strptime(target_date, "%Y-%m-%d")
        result = []

        for pkg in packages:
            try:
                start_date = datetime.strptime(pkg["start_date"], "%Y-%m-%d")
                diff = abs((start_date - target).days)

                if diff <= 30:  # В пределах месяца
                    result.append(pkg)
            except:
                pass

        # Сортируем по близости к дате
        result.sort(key=lambda p: abs((datetime.strptime(p["start_date"], "%Y-%m-%d") - target).days))

        return result

    def get_package_by_id(self, package_id: str) -> dict:
        """Получить пакетный тур по ID"""
        packages = self.data.get("packages", [])
        for package in packages:
            if package["id"] == package_id:
                return package
        return None