FROM mcr.microsoft.com/playwright/python:v1.50.0-noble
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN patchright install
RUN patchright install-deps

COPY . .

CMD ["python", "main.py"]
