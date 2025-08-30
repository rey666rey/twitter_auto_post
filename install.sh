#!/bin/bash
set -e

echo "🚀 Устанавливаю Docker и зависимости..."

# Обновляем пакеты
sudo apt-get update

sudo apt install speedtest-cli

# Ставим зависимости для apt
sudo apt-get install -y ca-certificates curl gnupg

# Создаём каталог для ключей
sudo install -m 0755 -d /etc/apt/keyrings

# Скачиваем GPG-ключ Docker
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc

# Даем права на чтение
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Добавляем репозиторий Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Обновляем индексы пакетов
sudo apt-get update

# Устанавливаем Docker и плагины
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Ставим зависимости для Playwright (чтобы браузеры работали в headless)
sudo apt-get install -y \
  libgtk-4-1 libavif13 libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
  libxfixes3 libxrandr2 libgbm1 libasound2

echo "✅ Docker и Playwright зависимости установлены!"