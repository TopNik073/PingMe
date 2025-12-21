# PingMe

PingMe - современный мессенджер с поддержкой реального времени через WebSocket, разработанный на FastAPI.

## Описание проекта

PingMe - это полнофункциональный мессенджер, предоставляющий REST API для управления пользователями, беседами и сообщениями, а также WebSocket API для обмена сообщениями в реальном времени. Проект реализует архитектуру Clean Architecture с четким разделением слоев.

## Основные возможности

### Аутентификация и пользователи

- Регистрация и вход с подтверждением через email
- JWT токены (access и refresh)
- OAuth авторизация через Google
- Управление профилем пользователя
- Загрузка аватаров пользователей
- Восстановление пароля

### Беседы

- Создание бесед (диалоги и групповые чаты)
- Автоматическое определение типа беседы по количеству участников
- Управление участниками (добавление, удаление, изменение ролей)
- Роли участников: OWNER, ADMIN, MEMBER
- Загрузка аватаров для групповых бесед
- Поиск бесед по названию
- Мягкое удаление бесед

### Сообщения

- Создание, редактирование и удаление сообщений
- Пересылка сообщений между беседами
- Прикрепление медиафайлов к сообщениям
- Отслеживание прочитанных сообщений (read receipts)
- Поиск сообщений по содержимому (full-text search)
- Пагинация сообщений

### WebSocket (реальное время)

- Обмен сообщениями в реальном времени
- Индикаторы печати (typing indicators)
- Read receipts с broadcast уведомлениями
- Подтверждения доставки (ACK)
- Heartbeat (ping/pong) для поддержания соединения
- Sequence numbers для упорядочивания сообщений
- Rate limiting для защиты от злоупотреблений
- Явные подписки на беседы
- Статусы пользователей (online/offline)

### Медиа

- Загрузка файлов в Yandex Object Storage (S3)
- Поддержка различных типов медиа
- Аватары для пользователей и бесед
- Публичный доступ к аватарам

### Дополнительные функции

- Кэширование в Redis
- Push-уведомления через Firebase Cloud Messaging (FCM)
- Логирование всех запросов и WebSocket соединений
- Миграции базы данных через Alembic

## Технологический стек

- **Framework**: FastAPI
- **База данных**: PostgreSQL 17
- **Кэш**: Redis 7
- **ORM**: SQLAlchemy 2.0 (async)
- **Миграции**: Alembic
- **Аутентификация**: JWT (python-jose)
- **Хранилище файлов**: Yandex Object Storage (boto3)
- **Email**: SMTP (aiosmtplib)
- **Push-уведомления**: Firebase Cloud Messaging
- **WebSocket**: websockets
- **Валидация**: Pydantic 2.10
- **Логирование**: structlog

## Структура проекта

Проект следует принципам Clean Architecture с разделением на слои:

```
src/
├── application/          # Слой бизнес-логики
│   ├── interfaces/      # Интерфейсы для зависимостей
│   └── services/        # Бизнес-сервисы
│       ├── auth_service.py
│       ├── conversation_service.py
│       ├── message_service.py
│       ├── media_service.py
│       └── user_service.py
│
├── infrastructure/      # Слой инфраструктуры
│   ├── cache/          # Redis кэширование
│   ├── database/       # Работа с БД
│   │   ├── models/     # SQLAlchemy модели
│   │   ├── repositories/  # Репозитории
│   │   └── enums/      # Перечисления
│   ├── email/          # SMTP сервис
│   ├── fcm/            # Firebase Cloud Messaging
│   ├── security/       # JWT обработка
│   ├── websocket/      # WebSocket обработка
│   │   ├── connection_manager.py
│   │   ├── handler.py
│   │   └── rate_limiter.py
│   └── yandex/         # Yandex S3 интеграция
│
├── presentation/        # Слой представления
│   ├── api/            # API роутеры
│   │   ├── v1/         # API версии 1
│   │   │   ├── auth/
│   │   │   ├── conversations/
│   │   │   ├── messages/
│   │   │   ├── media/
│   │   │   ├── users/
│   │   │   └── websocket/
│   │   ├── guards/     # JWT guards
│   │   └── dependencies/  # DI контейнер
│   ├── schemas/        # Pydantic схемы
│   ├── middlewares/    # Middleware
│   └── utils/          # Утилиты
│
└── core/               # Ядро приложения
    ├── config.py       # Конфигурация
    ├── logging.py      # Настройка логирования
    ├── exceptions.py   # Исключения
    └── startup.py      # Инициализация сервисов
```

## Требования

- Python 3.12+
- PostgreSQL 17+
- Redis 7+
- Yandex Object Storage (или совместимое S3 хранилище)
- SMTP сервер (для отправки email)
- Firebase Cloud Messaging credentials (опционально, для push-уведомлений)

## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd PingMe
```

### 2. Установка зависимостей

Проект использует [*uv*](https://docs.astral.sh/uv/getting-started/installation/) для управления зависимостями:

```bash
# Установка зависимостей проекта
uv sync
```

### 3. Настройка окружения

Создайте файл `.env` в корне проекта на основе примера:

```env
# Приложение
APP_HOST=127.0.0.1
APP_PORT=8000
APP_NAME=PingMe
DEBUG=False

# База данных
DB_USER=postgres
DB_PASS=<YOUR_STRONG_PASSWORD>
DB_HOST=localhost <db if run in docker>
DB_PORT=5432
DB_NAME=pingme

# Redis
REDIS_HOST=localhost <redis if run in docker>
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<YOUR_STRONG_PASSWORD>

# JWT
JWT_SECRET_KEY=<YOUR_LONG_LONG_SECRET_STRING>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1800
JWT_REFRESH_TOKEN_EXPIRE_DAYS=2592000

# Google OAuth (Not ready to use)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com

# Yandex S3
S3_BUCKET=<YOUR_BUCKET_NAME>
S3_ENDPOINT=https://storage.yandexcloud.net
S3_REGION=ru-central1
S3_ACCESS_KEY=<YOUR_ACCESS_KEY>
S3_SECRET_KEY=<YOUR_SECRET_KEY>

# FCM (Optionally)
FCM_CREDENTIALS_PATH=./credentials.json
```

### 4. Запуск через Docker Compose (рекомендуется)

```bash
# Запуск всех сервисов (PostgreSQL, Redis, приложение)
docker compose -f docker-compose.local.yml up --build
```

### 5. Запуск вручную

#### 5.1. Запуск PostgreSQL и Redis

Убедитесь, что PostgreSQL и Redis запущены и доступны.

#### 5.2. Применение миграций

```bash
# Активация виртуального окружения
# MacOS:
source .venv/bin/activate

# Windows
.venv/Scripts/activate

# Применение миграций
alembic upgrade head
```

#### 5.3. Запуск приложения

```bash
# Через uvicorn
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

# Или через Python
python -m src.main
```

### 6. Проверка работоспособности

После запуска приложение будет доступно по адресу:
- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Документация API

### REST API (FastAPI)

FastAPI автоматически генерирует интерактивную документацию:

1. **Swagger UI**: http://localhost:8000/docs
   - Интерактивный интерфейс для тестирования API
   - Возможность отправлять запросы прямо из браузера
   - Возможность авторизации через JWT токены

2. **ReDoc**: http://localhost:8000/redoc
   - Альтернативный формат документации
   - Удобен для чтения и изучения API

3. **OpenAPI спецификация**: http://localhost:8000/openapi.json
   - JSON схема API
   - Может быть импортирована в Postman, Insomnia и другие инструменты

### WebSocket API (AsyncAPI)

Для просмотра спецификации WebSocket протокола:

1. Откройте файл `docs/asyncapi.yml` в редакторе
2. Или загрузите файл на https://studio.asyncapi.com
   - Перейдите на сайт
   - Нажмите иконку импорта -> "Load File" или вставьте содержимое `docs/asyncapi.yml`
   - Просмотрите интерактивную документацию WebSocket протокола

Подробное описание WebSocket протокола также доступно в файле `tests/README_WEBSOCKET.md`.

## Тестирование

### Тестирование WebSocket

В проекте есть комплексный тестовый клиент для проверки всех функций WebSocket:

```bash
# Редактируйте конфигурацию в tests/test_websocket_client.py
# Затем запустите:
python tests/test_websocket_client.py
```

Подробная инструкция по использованию тестового клиента находится в `tests/README_WEBSOCKET.md`.

## Разработка

### Линтинг и форматирование

Проект использует `ruff` для линтинга и форматирования:

```bash
# Форматирование кода
ruff format .

# Проверка кода
ruff check src/

# Автоматическое исправление
ruff check --fix src/
```

Или используйте `justfile`:

```bash
# Форматирование
just ruff-format

# Проверка
just ruff-check

# Все проверки
just lint
```

### Миграции базы данных

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "описание изменений"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

## Конфигурация

Все настройки приложения находятся в `src/core/config.py` и загружаются из переменных окружения (файл `.env`).

### Основные настройки WebSocket

- `WS_HEARTBEAT_INTERVAL` - Интервал отправки ping (по умолчанию: 30 секунд)
- `WS_HEARTBEAT_TIMEOUT` - Таймаут отключения при отсутствии ping (по умолчанию: 60 секунд)
- `WS_TYPING_TIMEOUT` - Автоматическая остановка индикатора печати (по умолчанию: 5 секунд)
- `WS_MAX_MESSAGE_SIZE` - Максимальный размер сообщения (по умолчанию: 64KB)
- `WS_RATE_LIMIT_MESSAGES_PER_MINUTE` - Лимит сообщений в минуту (по умолчанию: 50)
- `WS_RATE_LIMIT_TYPING_PER_MINUTE` - Лимит typing индикаторов в минуту (по умолчанию: 30)
- `WS_RATE_LIMIT_GENERAL_PER_MINUTE` - Общий лимит запросов в минуту (по умолчанию: 150)

## Архитектура

Проект следует принципам Clean Architecture:

1. **Presentation Layer** (`src/presentation/`) - API роутеры, схемы, middleware
2. **Application Layer** (`src/application/`) - Бизнес-логика, сервисы
3. **Infrastructure Layer** (`src/infrastructure/`) - Реализация интерфейсов (БД, кэш, внешние сервисы)
4. **Core** (`src/core/`) - Общие компоненты (конфигурация, логирование, исключения)

Такая архитектура обеспечивает:
- Независимость бизнес-логики от инфраструктуры
- Легкое тестирование
- Возможность замены компонентов
- Четкое разделение ответственности

## Безопасность

- JWT токены для аутентификации
- Хеширование паролей (argon2)
- Rate limiting для WebSocket
- Валидация всех данных через Pydantic
- CORS настройки
- Защита от SQL инъекций (SQLAlchemy ORM)
- Логирование без чувствительных данных
