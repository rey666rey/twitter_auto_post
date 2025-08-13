# Базовый образ с Python и Playwright
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

# Рабочая директория в контейнере
WORKDIR /app

# Копируем файлы зависимостей (если есть requirements.txt)
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

RUN patchright install
# Копируем весь проект
COPY . .

# Команда запуска бота
CMD ["python", "main.py"]