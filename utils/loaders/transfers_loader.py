"""Загрузчик данных для трансферов"""
import json
import os
import logging

logger = logging.getLogger(__name__)


class TransfersLoader:
    """Класс для работы с трансферами (из JSON)"""

    def __init__(self, json_path: str = "data/mock_data.json"):
        self.json_path = json_path
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Загрузить данные из JSON"""
        if not os.path.exists(self.json_path):
            return {
                "transfers": [],
                "users": {},
                "orders": []
            }

        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_transfers_by_island(self, island: str = None) -> list:
        """
        Получить трансферы по острову

        Args:
            island: код острова (если None - все трансферы)
        """
        transfers = self.data.get("transfers", [])

        if not island:
            return transfers

        # Фильтр по острову
        return [t for t in transfers if t["island"] == island]

    def get_transfer_by_id(self, transfer_id: str) -> dict:
        """Получить трансфер по ID"""
        transfers = self.data.get("transfers", [])
        for transfer in transfers:
            if transfer["id"] == transfer_id:
                return transfer
        return None
