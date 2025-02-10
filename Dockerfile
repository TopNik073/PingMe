FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev

# Копирование requirements
COPY requirements.txt .

# Установка зависимостей
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Копирование исходного кода
COPY . .

# Запуск миграций и приложения
CMD while ! nc -z db 5432; do sleep 0.1; done && \
    alembic upgrade head && \
    uvicorn main:app --host 0.0.0.0 --port 8000 