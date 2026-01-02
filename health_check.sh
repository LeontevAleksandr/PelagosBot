#!/bin/bash
# Быстрый healthcheck для бота

echo "=== Pelagos Bot Health Check ==="
echo ""

# Проверка статуса контейнеров
echo "Статус контейнеров:"
docker compose ps

echo ""
echo "Здоровье контейнеров:"
docker ps --filter "name=pelagos" --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "Последние логи бота (10 строк):"
docker compose logs --tail=10 pelagos-bot

echo ""
echo "Redis статус:"
docker compose exec -T redis redis-cli ping 2>/dev/null || echo "Redis недоступен"