# Используем официальный образ Python 3.13
FROM python:3.13-slim

# Устанавливаем необходимые системные зависимости
RUN apt-get update && apt-get install -y \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libnss3 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgtk-3-0 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    wget \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libu2f-udev \
    libvulkan1 \
    libnss3 \
    xdg-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем Playwright и браузеры
RUN pip install --no-cache-dir playwright && \
    playwright install --with-deps

# Устанавливаем зависимости проекта
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в контейнер
COPY . .

# Указываем команду для запуска бота
CMD ["python", "main.py"]
