# ErrorLens — AI-powered QA Platform

## Проект

| Поле | Значение |
|------|----------|
| Name | ErrorLens |
| Type | AI-powered QA platform — генерация тест-сьютов через LLM |
| Repo | github.com/Mdyuzhev/errorlens |
| Запуск | Docker Compose (`docker/docker-compose.yml`) |

## Стек

| Слой | Технология |
|------|------------|
| Backend | Python 3.11, FastAPI, SQLAlchemy async, Alembic |
| Database | PostgreSQL 16 (единственная БД, SQLite убран) |
| Frontend | Vue 3, Vite 7, Pinia, TailwindCSS 4 |
| LLM | Anthropic, OpenAI, Groq, Gemini, Ollama, GigaChat |
| Auth | JWT (access 30min, refresh 7days) |
| Инфраструктура | Docker Compose (nginx + backend + postgres) |

## Архитектура

```
Router → Service → Repository → Model
```

Нарушения архитектуры запрещены. Router не содержит бизнес-логику. Service не импортирует Router.

## Структура проекта

```
errorlens/
├── .claude/
│   ├── CLAUDE.md              # этот файл
│   ├── settings.json          # разрешения (Bash)
│   └── commands/              # slash-команды агента
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entrypoint + lifespan
│   │   ├── config.py          # Settings (pydantic-settings)
│   │   ├── database.py        # SQLAlchemy async engine + sessions
│   │   ├── models/            # SQLAlchemy модели (db_models.py, user.py)
│   │   ├── routers/           # FastAPI роутеры
│   │   ├── services/          # Бизнес-логика
│   │   └── websocket/         # WebSocket для generation progress
│   ├── tests/                 # pytest тесты
│   ├── alembic/               # Миграции БД
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard-vue/
│   ├── src/
│   │   ├── views/             # Vue pages
│   │   ├── components/        # Reusable components
│   │   ├── stores/            # Pinia stores
│   │   ├── services/api.js    # Axios API client
│   │   └── router/index.js    # Vue Router (hash mode)
│   ├── package.json
│   └── vite.config.js
├── docker/
│   ├── docker-compose.yml     # postgres + backend + nginx
│   └── Dockerfile             # Full-stack single-container
├── nginx/
│   ├── Dockerfile             # Multi-stage: Vue build + nginx
│   └── nginx.conf             # Proxy /api/ → backend, /dashboard/ → Vue
├── bookmarklet/               # Browser recorder
├── landing/                   # Static landing page
├── Tasks/                     # Задачи для агента
│   ├── TASK-NNN-*.md          # В очереди
│   └── done/                  # Выполненные
├── .env                       # Переменные окружения
└── .env.example
```

## Docker Compose

Единственный способ запуска. Три сервиса:

| Сервис | Порт | Назначение |
|--------|------|------------|
| postgres | 5432 | PostgreSQL 16 |
| backend | 8000 | FastAPI + uvicorn |
| nginx | 3000 | Landing + Vue dashboard + API proxy |

```bash
cd docker && docker compose up --build
```

| URL | Назначение |
|-----|------------|
| http://localhost:3000 | Landing page |
| http://localhost:3000/dashboard/ | Vue Dashboard |
| http://localhost:3000/api/ | API через nginx proxy |
| http://localhost:8000 | API напрямую |
| http://localhost:8000/docs | Swagger |

## API Routes

Backend роуты БЕЗ префикса `/api`. Nginx проксирует `/api/` → backend `/`.

Основные группы: `/auth/*`, `/sessions/*`, `/testcases/*`, `/tasks/*`, `/articles/*`, `/test-runs/*`, `/tests/*`, `/integrations/*`, `/analyze/*`, `/projects/*`, `/generation/*`, `/ws/*`

## Требования к коду

### Python

| Требование | Детали |
|------------|--------|
| Type hints | Все функции, все параметры |
| Async | Все I/O операции |
| Max file size | 500 LOC |
| Exceptions | Specific types only, нет bare `except` |
| Memory | Явный cleanup, TTL для кэшей |

### Memory Management

```python
MAX_AGE = 3600  # TTL cleanup для всех кэшей
MAX_ITEMS = 10000
```

### Тесты

Required per feature:
- `test_empty_input()`
- `test_none_handling()`
- `test_duplicate_handling()`
- `test_concurrent_access()`
- `test_memory_cleanup()`
- `test_error_recovery()`

### WebSocket

| Требование | Значение |
|------------|----------|
| State storage | Redis or DB, not in-memory |
| Reconnection | Exponential backoff client-side |
| Timeout | 120s max |
| Cleanup | Explicit on disconnect |

## Git

| Параметр | Значение |
|----------|----------|
| Branch | main |
| Commit lang | Русский с английским префиксом |
| Commit format | `[prefix] Описание` |

Префиксы: `[backend]`, `[frontend]`, `[docker]`, `[infra]`, `[docs]`, `[test]`, `[fix]`, `[refactor]`

## Slash-команды

| Команда | Назначение |
|---------|------------|
| `/start` | Загрузить контекст, показать статус проекта |
| `/status` | Детальный отчёт: git, тесты, docker, задачи |
| `/task` | Взять задачу из Tasks/, выполнить, переместить в done/ |
| `/test` | Запустить pytest, показать покрытие |
| `/push` | Тесты → commit → push (стоп если тесты падают) |
| `/review` | Ревью: стиль, архитектура, тесты, безопасность |
| `/docker` | Docker Compose: up / down / logs / rebuild / ps |
| `/migrate` | Alembic: status / create / up / down |
| `/refresh_docs` | Обновить CLAUDE.md, README, .env.example |

## Управление задачами

- `Tasks/TASK-NNN-name.md` — задачи в очереди
- `Tasks/done/` — выполненные (перемещаются после завершения)
- Формат: таблицы + сигнатуры + assertions, без готового кода

## Запрещено

- Skip phases
- Bare `except:`
- In-memory state for distributed (use Redis/DB)
- Files >500 LOC
- Commit without tests
- Ask confirmation
- Multiple solution options
- Best practices essays

## Quality Gates

Задача завершена когда:
- [ ] Все тесты проходят
- [ ] Нет bare except
- [ ] Memory cleanup есть
- [ ] Concurrent access протестирован
- [ ] Edge cases покрыты
- [ ] <500 LOC per file

## Instruction Format

Инструкции для агента содержат:
- Interface signatures
- Requirements list (таблицы)
- Prohibited patterns
- Test cases

Инструкции НЕ содержат:
- Полные реализации
- Ready-to-copy code

Агент пишет код самостоятельно.

## Known Issues & Fixes

### Sessions API
- Sessions list returns `{items: [], total: N}` → store использует `response.data.items || response.data`
- Sessions без `project_id` (bookmarklet) → `include_unassigned=True` param

### Session Detail Modal
- `openSession()` → fetch full session via `store.fetchSession(id)`
- Analyze → `/analyze/rerun` с `{session_id: id}` body

### Bookmarklet
- `LOCAL_DASHBOARD_URL` → `http://localhost:5173` (dev) или `http://localhost:3000/dashboard/` (docker)

### API Routes
- Backend routes: `/auth/*`, `/sessions/*` (без /api prefix)
- Nginx proxy: `/api/sessions/*` → backend `/sessions/*`
