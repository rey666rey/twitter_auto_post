#!/bin/bash
set -e

cd ~/twitter_auto_post

echo "📥 Обновляю код..."
git fetch origin dev
git reset --hard origin/dev

echo "🐳 Перезапускаю контейнеры..."
docker compose down
docker compose up -d --build

echo "✅ Деплой завершён!"
