#!/bin/bash
set -e

echo "🚀 Starting deployment..."

# Проверка что скрипт не запущен от root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Error: Do not run this script as root!"
    exit 1
fi

cd "$(dirname "$0")"

echo "📥 Git pull..."
git pull origin production

export GIT_COMMIT=$(git rev-parse --short HEAD)
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "📦 Building with GIT_COMMIT=$GIT_COMMIT, GIT_BRANCH=$GIT_BRANCH"

echo "🔨 Building Docker image..."
docker compose build --build-arg GIT_COMMIT=$GIT_COMMIT pelagos-bot

echo "🔄 Restarting container..."
docker compose up -d --force-recreate pelagos-bot

echo "✅ Deployment completed!"
echo "📦 Version: $GIT_COMMIT ($GIT_BRANCH)"
