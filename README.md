# ErrorLens

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/vue-3-brightgreen.svg)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://docs.docker.com/compose/)

AI-powered QA платформа. Записывает ошибки браузера, анализирует через LLM, генерирует тест-кейсы и тест-сьюты.

## Возможности

### Запись и анализ ошибок
- **Букмарклет-рекордер** — запись JS-ошибок, console.log, HTTP-запросов прямо в браузере
- **AI-анализ** — автоматический анализ через Groq, Gemini, OpenAI, Anthropic, Ollama, GigaChat
- **Severity detection** — определение критичности ошибок

### Dashboard
- **Sessions** — история записанных сессий с фильтрацией и поиском
- **Test Cases** — управление тест-кейсами с папками, приоритетами, шагами
- **Tasks** — Kanban-доска задач (todo / in progress / done)
- **Articles** — база знаний с категориями и тегами
- **Results** — результаты тестовых прогонов со статистикой
- **Generator** — генерация тест-сьютов из сессий через LLM

### Генерация тестов
- **pytest** — Python тесты
- **REST Assured** — Java тесты
- **Cypress** — E2E тесты
- **Postman** — коллекции для API
- **k6** — нагрузочные тесты
- **TestIT** — экспорт в TMS

### Интеграции
- **TestIT** — экспорт тест-кейсов в Test Management System
- **JWT-авторизация** — access/refresh токены, ролевая модель
- **Проекты** — мультипроектность с ролями (owner, admin, member, viewer)

## Стек

| Слой | Технология |
|------|------------|
| Backend | Python 3.11, FastAPI, SQLAlchemy async, Alembic |
| Database | PostgreSQL 16 |
| Frontend | Vue 3, Vite, Pinia, TailwindCSS |
| LLM | Groq, Gemini, OpenAI, Anthropic, Ollama, GigaChat |
| Auth | JWT (access 30 min, refresh 7 days) |
| Infra | Docker Compose (nginx + backend + postgres) |

## Запуск через Docker Compose

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Mdyuzhev/errorlens.git
cd errorlens
```

### 2. Создать `.env` файл

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# PostgreSQL
POSTGRES_PASSWORD=errorlens_secret

# LLM (нужен хотя бы один ключ)
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key

# Auth
ADMIN_PASSWORD=your_admin_password
ADMIN_KEY=your_admin_key
```

### 3. Запустить

```bash
cd docker
docker compose up --build
```

### 4. Открыть

| URL | Назначение |
|-----|------------|
| http://localhost:3000 | Landing page |
| http://localhost:3000/dashboard/ | Vue Dashboard |
| http://localhost:3000/api/ | API через nginx |
| http://localhost:8000 | API напрямую |
| http://localhost:8000/docs | Swagger UI |

### Учётные данные

При первом запуске автоматически создаётся пользователь `admin` с паролем из переменной `ADMIN_PASSWORD` (по умолчанию `change_me_in_env`). Также создаётся пользователь `demo` с паролем `ErrorLenseTest` и набор демо-данных (тест-кейсы, задачи, статьи).

## Docker Compose: управление

```bash
# Запуск
cd docker && docker compose up --build -d

# Статус
docker compose -f docker/docker-compose.yml ps

# Логи
docker compose -f docker/docker-compose.yml logs -f backend
docker compose -f docker/docker-compose.yml logs -f nginx

# Остановка
docker compose -f docker/docker-compose.yml down

# Полная очистка (включая данные БД)
docker compose -f docker/docker-compose.yml down -v
```

## Сервисы

| Сервис | Образ | Порт | Описание |
|--------|-------|------|----------|
| postgres | postgres:16-alpine | 5432 | БД PostgreSQL |
| backend | python:3.11 + FastAPI | 8000 | API сервер |
| nginx | nginx:alpine + Vue build | 3000 | Reverse proxy + SPA |

## Локальная разработка (без Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Нужен PostgreSQL или задайте DATABASE_URL
cp ../.env.example ../.env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd dashboard-vue
npm install
npm run dev
```

Dashboard будет доступен на `http://localhost:5173`.

## Конфигурация (.env)

| Переменная | Обязательна | Описание |
|------------|:-----------:|----------|
| `POSTGRES_PASSWORD` | да | Пароль PostgreSQL |
| `LLM_PROVIDER` | да | Провайдер LLM: `groq`, `gemini`, `openai`, `anthropic`, `ollama`, `gigachat` |
| `GROQ_API_KEY` | * | API ключ Groq |
| `GEMINI_API_KEY` | * | API ключ Google Gemini |
| `OPENAI_API_KEY` | * | API ключ OpenAI |
| `ANTHROPIC_API_KEY` | * | API ключ Anthropic |
| `ADMIN_PASSWORD` | нет | Пароль admin-пользователя (default: `change_me_in_env`) |
| `ADMIN_KEY` | нет | Ключ доступа к admin API |
| `TESTIT_URL` | нет | URL инстанса TestIT |
| `TESTIT_TOKEN` | нет | API токен TestIT |
| `TESTIT_PROJECT_ID` | нет | GUID проекта в TestIT |

\* Нужен хотя бы один API ключ для выбранного провайдера.

### Получение API ключей

- **Groq** (рекомендуется): [console.groq.com](https://console.groq.com) — бесплатно, быстро
- **Gemini**: [aistudio.google.com](https://aistudio.google.com) — щедрый бесплатный tier
- **OpenAI**: [platform.openai.com](https://platform.openai.com)
- **Anthropic**: [console.anthropic.com](https://console.anthropic.com)

## API

### Основные эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Health check |
| POST | `/auth/login` | Авторизация (JWT) |
| GET | `/sessions` | Список сессий |
| GET | `/sessions/{id}` | Детали сессии |
| POST | `/analyze` | AI-анализ ошибок |
| POST | `/analyze/rerun` | Повторный анализ |
| GET | `/testcases` | Список тест-кейсов |
| POST | `/testcases` | Создать тест-кейс |
| GET | `/tasks` | Список задач |
| GET | `/tasks/board` | Kanban-доска |
| GET | `/articles` | Список статей |
| GET | `/test-runs` | Прогоны тестов |
| POST | `/generation/generate` | Генерация тест-сьюта через LLM |
| GET | `/projects` | Список проектов |

Полная документация: http://localhost:8000/docs (Swagger UI).

## Архитектура

```
Router (HTTP) → Service (Business Logic) → Repository (Data Access) → Model (DB)
```

```
errorlens/
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── main.py           # Entrypoint + lifespan
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   ├── database.py       # SQLAlchemy async engine
│   │   ├── models/           # SQLAlchemy модели
│   │   ├── repositories/     # Data Access Layer
│   │   ├── services/         # Business Logic
│   │   ├── routers/          # API endpoints
│   │   ├── middleware/        # JWT auth, rate limiting
│   │   ├── generators/       # Генераторы тестов (pytest, cypress, k6...)
│   │   └── websocket/        # WebSocket для progress
│   ├── tests/                # pytest (300+ тестов)
│   └── alembic/              # Миграции БД
├── dashboard-vue/            # Vue 3 SPA
│   └── src/
│       ├── views/            # Pages (Dashboard, TestCases, Tasks, Articles...)
│       ├── components/       # Reusable components
│       ├── stores/           # Pinia stores
│       └── services/         # Axios API client
├── bookmarklet/              # Browser recorder (JS)
├── landing/                  # Static landing page
├── docker/
│   └── docker-compose.yml    # PostgreSQL + Backend + Nginx
└── nginx/
    ├── Dockerfile            # Multi-stage: Vue build + nginx
    └── nginx.conf            # Proxy config
```

## Local GitLab for CI Testing

Локальный GitLab CE для тестирования интеграции ErrorLens с CI/CD пайплайнами. Живёт в отдельном Docker Compose файле, изолированно от основного проекта.

**Требования:** 4 CPU, 6 GB свободной RAM.

```bash
# Запуск
cd infra/gitlab
docker compose up -d

# Первоначальная настройка (создаёт токен, группу, проект, runner)
./setup.sh

# Остановка
./teardown.sh
```

Подробнее: [infra/gitlab/README.md](infra/gitlab/README.md)

## Лицензия

MIT — см. [LICENSE](LICENSE).
