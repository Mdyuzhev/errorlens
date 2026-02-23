# TASK: Удаление Railway, переход на Docker + PostgreSQL

## Цель

Полностью убрать Railway-деплой из проекта. Перевести приложение с SQLite на PostgreSQL. Единственный способ запуска — Docker Compose.

## Контекст

Сейчас в проекте два режима работы с БД: SQLite (локальная разработка) и PostgreSQL (Railway). Railway больше не используется. Нужно оставить только PostgreSQL через Docker.

---

## Часть 1: Добавить PostgreSQL в docker-compose

### Файл: `docker/docker-compose.yml`

| Сервис | Образ | Порты | Параметры |
|--------|-------|-------|-----------|
| `postgres` | `postgres:16-alpine` | `5432:5432` | POSTGRES_DB=errorlens, POSTGRES_USER=errorlens, POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-errorlens_secret} |
| `backend` | build ../backend | 8000:8000 | depends_on postgres (condition: service_healthy), DATABASE_URL через environment |
| `nginx` | build context .. dockerfile nginx/Dockerfile | 3000:80 | depends_on backend |

Требования к сервису `postgres`:
- Volume: `postgres_data:/var/lib/postgresql/data`
- Healthcheck: `pg_isready -U errorlens -d errorlens`
- restart: unless-stopped

Требования к сервису `backend`:
- environment: `DATABASE_URL=postgresql+asyncpg://errorlens:${POSTGRES_PASSWORD:-errorlens_secret}@postgres:5432/errorlens`
- Убрать volume `../data:/app/data` (SQLite data больше не нужен)
- depends_on postgres с condition: service_healthy

В конце файла секция volumes:
```yaml
volumes:
  postgres_data:
```

---

## Часть 2: Убрать SQLite fallback из кода

### Файл: `backend/app/database.py`

Текущая логика (УДАЛИТЬ):
```python
if DATABASE_URL:
    # Railway/Heroku PostgreSQL
    ...
else:
    # Local dev - SQLite
    DATABASE_URL = "sqlite+aiosqlite:///./data/errorlens.db"
```

Заменить на:
```python
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

# Normalize driver for async
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
```

Убрать `aiosqlite` из `requirements.txt`.

### Файл: `backend/alembic/env.py`

Текущая логика (УДАЛИТЬ):
```python
if DATABASE_URL:
    ...
else:
    DATABASE_URL = "sqlite:///./data/errorlens.db"
```

Заменить на:
```python
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required for migrations")

# Alembic uses sync driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if "asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
if "aiosqlite" in DATABASE_URL:
    raise RuntimeError("SQLite is no longer supported. Use PostgreSQL.")
```

---

## Часть 3: Удалить Railway-артефакты

| Действие | Путь |
|----------|------|
| Удалить файл | `deploy/railway.json` |
| Удалить файл | `.github/workflows/post-deploy-tests.yml` |
| Удалить директорию | `deploy/` (если пуста после удаления railway.json) |
| Удалить файл | `backend/data/errorlens.db` (если существует) |
| Удалить файл | `backend/errorlens.db` (если существует) |

### Файл: `.github/workflows/ci.yml`

В job `test` добавить PostgreSQL service container:

```yaml
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: errorlens_test
          POSTGRES_USER: errorlens
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd="pg_isready -U errorlens -d errorlens_test"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
```

В step `Run tests` добавить env:
```yaml
        env:
          DATABASE_URL: postgresql+asyncpg://errorlens:test_password@localhost:5432/errorlens_test
          GEMINI_API_KEY: ""
          GROQ_API_KEY: ""
```

---

## Часть 4: Обновить .env файлы

### Файл: `.env.example` (корень проекта)

Добавить:
```
# Database (PostgreSQL)
POSTGRES_PASSWORD=errorlens_secret
DATABASE_URL=postgresql+asyncpg://errorlens:errorlens_secret@postgres:5432/errorlens
```

### Файл: `backend/.env.example`

Добавить:
```
# Database (required)
DATABASE_URL=postgresql+asyncpg://errorlens:errorlens_secret@localhost:5432/errorlens
```

### Файл: `.env` (корень проекта)

Добавить:
```
POSTGRES_PASSWORD=errorlens_secret
```

НЕ добавлять DATABASE_URL в корневой `.env` — он задаётся в docker-compose.yml через environment.

---

## Часть 5: Обновить backend Dockerfile

### Файл: `backend/Dockerfile`

Убрать строку `RUN mkdir -p /app/data` — SQLite data directory больше не нужен.

### Файл: `docker/Dockerfile` (full-stack)

Убрать строку `RUN mkdir -p /app/data` — SQLite data directory больше не нужен.

---

## Часть 6: Обновить requirements.txt

### Файл: `backend/requirements.txt`

| Действие | Пакет | Причина |
|----------|-------|---------|
| УДАЛИТЬ | `aiosqlite>=0.19.0` | SQLite больше не используется |
| ОСТАВИТЬ | `asyncpg>=0.29.0` | Async PostgreSQL driver |
| ОСТАВИТЬ | `psycopg2-binary>=2.9.9` | Sync driver для Alembic |
| ОСТАВИТЬ | `sqlalchemy>=2.0.0` | ORM |
| ОСТАВИТЬ | `alembic>=1.13.0` | Миграции |

---

## Часть 7: Убрать упоминания Railway из комментариев

Пройти grep по проекту и заменить/удалить комментарии:

| Файл | Найти | Заменить |
|------|-------|----------|
| `backend/app/database.py` | Комментарии про "Railway/Heroku", "Local dev - SQLite" | Убрать, оставить чистый PostgreSQL код |
| `backend/alembic/env.py` | "Railway/Heroku PostgreSQL", "Local dev - SQLite" | Убрать |
| `docker/Dockerfile` | "for Railway" в комментарии | "Full Stack Dockerfile" |
| Любой файл | `errorlens-production.up.railway.app` | Удалить или заменить на localhost |

---

## Запрещено

- Оставлять SQLite fallback "на всякий случай"
- Оставлять файлы Railway
- Добавлять опцию выбора SQLite/PostgreSQL через env
- Менять структуру моделей или бизнес-логику

---

## Критерии готовности

| Проверка | Команда / условие |
|----------|-------------------|
| Docker Compose запускается | `cd docker && docker-compose up --build` — все 3 сервиса healthy |
| PostgreSQL работает | `docker exec <container> pg_isready` возвращает 0 |
| Backend стартует | `curl http://localhost:8000/health` → `{"status":"ok"}` |
| Dashboard открывается | `http://localhost:3000/dashboard/` → Vue app |
| API через nginx | `curl http://localhost:3000/api/health` → `{"status":"ok"}` |
| Login работает | POST `/api/auth/login` с demo/ErrorLenseTest → access_token |
| Нет SQLite в коде | `grep -r "sqlite" backend/app/` → пусто |
| Нет Railway файлов | `deploy/railway.json` не существует |
| CI тесты с PostgreSQL | `.github/workflows/ci.yml` использует postgres service |
| `aiosqlite` удалён | Нет в `requirements.txt` |
| Данные persist | `docker-compose down && docker-compose up` → данные на месте (volume) |

---

## Время: 1-2 часа
