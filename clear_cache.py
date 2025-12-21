#!/usr/bin/env python3
"""
Скрипт для очистки Redis кэша

Использование:
    python clear_cache.py              # Очистить весь кэш
    python clear_cache.py --pattern room:price:*  # Очистить только кэш цен
    python clear_cache.py --pattern transfers:*   # Очистить только кэш трансферов
    python clear_cache.py --stats      # Показать статистику кэша
"""

import argparse
import redis
import sys


def get_redis_client():
    """Подключиться к Redis"""
    try:
        client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2
        )
        # Проверяем соединение
        client.ping()
        return client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"❌ Не удалось подключиться к Redis: {e}")
        print("   Убедитесь что Redis запущен: redis-server")
        sys.exit(1)


def clear_all_cache(client):
    """Очистить весь кэш"""
    try:
        client.flushdb()
        print("✅ Весь кэш успешно очищен!")
        return True
    except Exception as e:
        print(f"❌ Ошибка очистки кэша: {e}")
        return False


def clear_cache_by_pattern(client, pattern):
    """Очистить кэш по паттерну"""
    try:
        keys = list(client.scan_iter(match=pattern))
        if not keys:
            print(f"ℹ️  Ключи по паттерну '{pattern}' не найдены")
            return True

        deleted = 0
        for key in keys:
            client.delete(key)
            deleted += 1

        print(f"✅ Удалено {deleted} ключей по паттерну '{pattern}'")
        return True
    except Exception as e:
        print(f"❌ Ошибка очистки кэша: {e}")
        return False


def show_cache_stats(client):
    """Показать статистику кэша"""
    try:
        info = client.info('stats')
        dbsize = client.dbsize()

        print("📊 Статистика Redis кэша:")
        print(f"   Всего ключей: {dbsize}")
        print(f"   Попадания (hits): {info.get('keyspace_hits', 0)}")
        print(f"   Промахи (misses): {info.get('keyspace_misses', 0)}")

        total = info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)
        if total > 0:
            hit_rate = (info.get('keyspace_hits', 0) / total) * 100
            print(f"   Hit rate: {hit_rate:.2f}%")

        # Показываем примеры ключей
        print("\n📋 Примеры ключей в кэше:")
        for key in list(client.scan_iter(count=10))[:10]:
            ttl = client.ttl(key)
            ttl_text = f"{ttl}s" if ttl > 0 else "∞"
            print(f"   • {key} (TTL: {ttl_text})")

        return True
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Управление Redis кэшем бота Pelagos'
    )
    parser.add_argument(
        '--pattern',
        type=str,
        help='Паттерн для удаления ключей (например: room:price:*)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Показать статистику кэша'
    )

    args = parser.parse_args()

    # Подключаемся к Redis
    client = get_redis_client()
    print(f"✅ Подключено к Redis: localhost:6379")

    # Выполняем команду
    if args.stats:
        show_cache_stats(client)
    elif args.pattern:
        clear_cache_by_pattern(client, args.pattern)
    else:
        # Подтверждение перед полной очисткой
        response = input("⚠️  Вы уверены что хотите очистить ВЕСЬ кэш? (yes/no): ")
        if response.lower() in ['yes', 'y', 'да']:
            clear_all_cache(client)
        else:
            print("❌ Отменено")


if __name__ == '__main__':
    main()
