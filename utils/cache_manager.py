"""Менеджер кэширования с использованием Redis
    python clear_cache.py
    python clear_cache.py --pattern "room:price:*" Очистит только цены
    python clear_cache.py --pattern "hotel:rooms:*" Очистит только номера отелей
    python clear_cache.py --stats Посмотреть статистику кэша


"""
import json
import logging
import os
from typing import Optional, Any
import redis
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """Менеджер для кэширования данных в Redis"""

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        """
        Инициализация Redis клиента

        Args:
            host: хост Redis сервера
            port: порт Redis сервера
            db: номер базы данных
        """
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Проверяем соединение
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"✅ Redis подключен: {host}:{port}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"⚠️ Redis недоступен, кэширование отключено: {e}")
            self.redis_client = None
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        """
        Получить значение из кэша

        Args:
            key: ключ для поиска

        Returns:
            Значение или None если не найдено
        """
        if not self.enabled:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"✓ Кэш HIT: {key}")
                return json.loads(value)
            logger.debug(f"✗ Кэш MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Ошибка чтения из кэша: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Сохранить значение в кэш

        Args:
            key: ключ для сохранения
            value: значение (будет сериализовано в JSON)
            ttl: время жизни в секундах (по умолчанию 5 минут)

        Returns:
            True если успешно, False иначе
        """
        if not self.enabled:
            return False

        try:
            json_value = json.dumps(value, ensure_ascii=False)
            self.redis_client.setex(key, timedelta(seconds=ttl), json_value)
            logger.debug(f"✓ Кэш SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Ошибка записи в кэш: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Удалить значение из кэша

        Args:
            key: ключ для удаления

        Returns:
            True если успешно, False иначе
        """
        if not self.enabled:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"✓ Кэш DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления из кэша: {e}")
            return False

    def flush_all(self) -> bool:
        """
        Очистить весь кэш

        Returns:
            True если успешно, False иначе
        """
        if not self.enabled:
            return False

        try:
            self.redis_client.flushdb()
            logger.info("✓ Кэш полностью очищен")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")
            return False

    def get_stats(self) -> dict:
        """
        Получить статистику кэша

        Returns:
            Словарь со статистикой или пустой словарь если Redis недоступен
        """
        if not self.enabled:
            return {'enabled': False}

        try:
            info = self.redis_client.info('stats')
            return {
                'enabled': True,
                'keys': self.redis_client.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {'enabled': False, 'error': str(e)}

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Вычислить hit rate в процентах"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)


# Глобальный экземпляр
_cache_manager_instance = None


def get_cache_manager() -> CacheManager:
    """Получить экземпляр CacheManager"""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        # Читаем настройки из переменных окружения
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', '6379'))
        _cache_manager_instance = CacheManager(host=host, port=port)
    return _cache_manager_instance


def set_cache_manager(host: str = 'localhost', port: int = 6379, db: int = 0):
    """Установить экземпляр CacheManager"""
    global _cache_manager_instance
    _cache_manager_instance = CacheManager(host=host, port=port, db=db)
