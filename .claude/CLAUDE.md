# ErrorLens — Agent Context

> 🎯 Это главный файл контекста. Claude Code читает его автоматически при старте сессии.

## Кто мы

- **Claude Opus** = "шеф" — стратегические решения, архитектура, планирование
- **Claude Code** = "коллега" — реализация, код, тесты
- Референс: "Следствие ведут Колобки" 🔍

---

## Общие принципы

- **Полная автономия**: принимай решения сам, не спрашивай подтверждений
- **Минимум слов**: краткие отчеты, никакой воды
- **Исправляй ошибки сразу**: не останавливайся на полпути
- **Все изменения коммитятся** с понятными сообщениями
- **Если что-то сломалось** - фиксишь и продолжаешь

---

## Проект

**ErrorLens** — AI-powered QA platform. Bookmarklet записывает browser errors/requests, отправляет на backend с LLM анализом. Zero-friction: drag-n-drop установка, работает на любом сайте.

**Production:** https://errorlens-production.up.railway.app
**Repo:** github.com/Mdyuzhev/errorlens (private)
**Demo:** demo / ErrorLenseTest

---

## Структура проекта

```
errorlens/
├── .claude/                # Конфигурация агента
│   ├── CLAUDE.md          # Этот файл (контекст)
│   └── settings.local.json # Настройки и permissions
│
├── .github/workflows/      # CI/CD
│   ├── ci.yml             # Basic CI
│   ├── deploy-landing.yml # Landing deployment
│   └── post-deploy-tests.yml # Post-deploy webhook
│
├── backend/               # FastAPI приложение
│   ├── app/              # Исходный код
│   ├── tests/            # Pytest тесты
│   ├── alembic/          # Миграции БД
│   └── requirements.txt
│
├── dashboard-vue/         # Vue 3 frontend
│   ├── src/              # Компоненты, views, stores
│   └── package.json
│
├── bookmarklet/           # Browser recorder
│   ├── src/              # ES модули
│   ├── dist/             # Собранные бандлы
│   └── package.json
│
├── docker/                # Docker конфигурация
│   ├── Dockerfile        # Production build
│   └── docker-compose.yml # Dev окружение
│
├── deploy/                # Deployment конфиги
│   └── railway.json      # Railway settings
│
├── docs/                  # Документация
│   ├── instructions/     # Инструкции для агентов
│   │   ├── archive/     # Завершённые waves
│   │   └── README.md
│   ├── Stage/           # K8s конфиги для stage
│   ├── ROADMAP.md       # План развития
│   ├── CONTRIBUTING.md  # Как контрибьютить
│   └── ...
│
├── landing/               # Landing page
├── nginx/                 # Nginx конфиг для prod
├── data/                  # SQLite DB (dev)
│
├── .secrets/              # Credentials (НЕ в git!)
│   ├── README.md
│   └── lab-credentials.md
│
├── .env.example          # Шаблон переменных окружения
├── pyproject.toml        # Python project config
├── README.md             # Главный README
└── LICENSE               # MIT
```

---

## Стек технологий

```
Backend:    Python 3.11 + FastAPI + SQLAlchemy (async) + Alembic
Database:   PostgreSQL (prod) / SQLite (dev)
Frontend:   Vue 3 + Vite + Pinia + TailwindCSS
Bookmarklet: Vanilla JS (IIFE) — сейчас рефакторим в модули
LLM:        Groq Llama 3.3 (primary) + Gemini 1.5 Flash (fallback)
Hosting:    Railway (backend + PostgreSQL)
Auth:       JWT (access 30min + refresh 7days)
```

---

## Архитектура Backend

```
backend/app/
├── main.py              # FastAPI entrypoint (~130 LOC)
├── config.py            # Pydantic Settings
├── database.py          # SQLAlchemy async engine
│
├── models/              # SQLAlchemy ORM
│   ├── db_models.py     # Session, TestCase, Task, Article, Project...
│   └── user.py          # User model
│
├── routers/             # API endpoints (thin controllers)
│   ├── sessions.py      # ✅ Service layer
│   ├── projects.py      # ✅ Service layer
│   ├── articles.py      # ✅ Service layer (Wave 3.2)
│   ├── tasks.py         # ✅ Service layer (Wave 3.2)
│   ├── testcases.py     # ✅ Service layer (Wave 3.2)
│   ├── testruns.py      # ✅ Service layer (Wave 3.2)
│   ├── analysis.py      # ✅ Service layer (Wave 3.2)
│   └── auth.py          # ✅ OK
│
├── services/            # Business logic
│   ├── session_service.py
│   ├── project_service.py
│   ├── article_service.py   # Wave 3.2
│   ├── task_service.py      # Wave 3.2
│   ├── testcase_service.py  # Wave 3.2
│   ├── testrun_service.py   # Wave 3.2
│   ├── analysis_service.py  # Wave 3.2
│   ├── export_service.py
│   ├── auth.py
│   └── seed_demo.py
│
├── repositories/        # Data access (CRUD)
│   ├── base.py          # Generic CRUD
│   ├── session_repo.py
│   ├── project_repo.py
│   ├── article_repo.py      # Wave 3.2
│   ├── task_repo.py         # Wave 3.2
│   ├── testcase_repo.py
│   ├── testrun_repo.py      # Wave 3.2
│   └── user_repo.py
│
├── generators/          # Test code generators
│   ├── postman.py, pytest.py, restassured.py
│   ├── k6.py, cypress.py, testit.py
│   └── ...
│
└── providers/           # LLM providers
    ├── groq.py, gemini.py
    └── base.py
```

**Правило:** Router → Service → Repository → Model. Не обходить!

---

## Архитектура Bookmarklet

**✅ Модуляризация завершена (Wave 3.2)**

```
bookmarklet/
├── src/                 # ES модули (source)
│   ├── index.js         # Entry point
│   ├── recorder.js      # Core recording logic
│   ├── network.js       # Fetch/XHR interception
│   ├── ui.js            # Widget UI
│   └── ...
│
├── dist/                # Собранные бандлы (esbuild)
│   ├── recorder.js      # Development build (30.9KB)
│   └── recorder.min.js  # Production build (19.6KB, -68%)
│
├── esbuild.config.js    # Build configuration
└── package.json         # npm scripts: build, build:min, watch
```

**Build:** `npm run build:all` → IIFE bundle из ES modules

---

## Завершённые Waves

### WAVE 3.2: Code Refactoring ✅ DONE

Цель: закрыть техдолг, сделать код правильным.

Результаты:
1. **Bookmarklet** ✅ — esbuild bundling, 68% size reduction
2. **Backend** ✅ — все роутеры используют Service layer (+5 services, +14 endpoints)
3. **Frontend** ✅ — split DashboardView (-71%), ResultsView (-79%)
4. **Tests & Docs** ✅ — 42 unit tests, architecture docs

### WAVE 3.3: QA Infrastructure ✅ DONE

Цель: автоматизация тестирования и изоляция multi-tenancy.

Результаты:
1. **Auto-seed test users** ✅ — 7 тестовых пользователей + 2 проекта при старте
2. **Post-Deploy Tests webhook** ✅ — автозапуск после push в main
3. **Multi-tenancy isolation fix** ✅ — articles теперь фильтруются по project_id
4. **Concurrency control** ✅ — дубликаты workflow отменяются

### WAVE 3.4: CI/CD Fix ✅ DONE

Цель: исправить CI pipeline, все тесты зелёные.

Результаты:
1. **black/isort/ruff formatting** ✅ — 54 файла отформатировано
2. **145/145 tests passing** ✅ — все тесты зелёные
3. **Logging improvements** ✅ — добавлен logging в POST /sessions

Тестовые пользователи:
| User | Password | Project | Role |
|------|----------|---------|------|
| owner1 | Test123! | Alpha | owner |
| owner2 | Test123! | Beta | owner |
| admin1 | Test123! | Alpha | admin |
| member1 | Test123! | Alpha | member |
| member2 | Test123! | Beta | member |
| viewer1 | Test123! | Alpha | viewer |
| viewer2 | Test123! | Beta | viewer |

---

## Backlog

См. `docs/ROADMAP.md`

---

## Git Workflow

```bash
# Ветки
main              # Production
feature/wave-3    # Текущая работа

# Коммиты
git commit -m "[Wave 3.2] Brief description in English"

# Push + PR
git push origin feature/wave-3
# Создать PR в GitHub UI
```

---

## Команды разработки

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd dashboard-vue
npm install
npm run dev

# Bookmarklet (после настройки esbuild)
cd bookmarklet
npm run build
npm run watch

# Тесты
cd backend && pytest -v
cd dashboard-vue && npm run test
```

---

## Важные файлы для чтения

При работе над задачей ОБЯЗАТЕЛЬНО прочитай:

| Задача | Файлы |
|--------|-------|
| Bookmarklet | `bookmarklet/src/`, legacy `bookmarklet/recorder.js` |
| Новый роутер | Образец: `routers/sessions.py` + `services/session_service.py` |
| Новый сервис | Образец: `services/session_service.py` + `repositories/session_repo.py` |
| Vue компонент | `dashboard-vue/src/views/DashboardView.vue` |
| Миграции | `backend/alembic/versions/` |

---

## Код стайл

### Python
```python
# Type hints везде
async def create_session(self, url: str, ...) -> dict:
    pass

# Docstrings для публичных методов
"""Create new session and trigger analysis."""

# Async для I/O
async with httpx.AsyncClient() as client:
    response = await client.post(...)
```

### JavaScript
```javascript
// ES6 modules в src/
export function createWidget() { }

// JSDoc для публичных функций
/**
 * Start recording browser events
 * @returns {void}
 */
export function startRecording() { }
```

### Vue
```vue
<!-- Composition API -->
<script setup>
import { ref, computed } from 'vue'
const items = ref([])
</script>

<!-- TailwindCSS классы -->
<template>
  <div class="p-4 bg-gray-100 rounded-lg">
</template>
```

---

## Чего НЕ делать

❌ Работать напрямую с моделями в роутерах
❌ Коммитить без тестирования
❌ Создавать файлы >500 LOC
❌ Хардкодить URL (использовать config)
❌ Забывать type hints
❌ Пушить в main напрямую
❌ Спрашивать "Хотите чтобы я...?" — просто делай
❌ Коммитить secrets/keys в репозиторий
❌ Удалять .gitignore, docker/docker-compose.yml без явного указания

---

## Workflow инструкций

1. Читай инструкцию полностью ДО начала работы
2. Проверяй какие файлы изменяются (view перед edit)
3. Делай изменения последовательно, по одному файлу
4. После каждого критического изменения — тест
5. Коммит после завершения логического блока работ
6. Финальный отчет по шаблону

---

## Обработка ошибок

**Если что-то не работает:**
1. Смотришь логи: `docker logs <container> --tail 50` или консоль
2. Пробуешь фикс
3. Если не помогло — откатываешь и пробуешь другой подход
4. **Максимум 3 попытки**, потом отчитываешься с деталями

**Типичные проблемы:**
- "Module not found" → pip install / npm install
- "Address already in use" → другой сервис на порту
- "API key invalid" → проверяешь .env
- "Connection refused" → проверяешь что сервис запущен

---

## Формат отчётов

**Финальный отчет** (после выполнения задачи):
```
✅ Выполнено:
- <список изменений>

🔧 Изменены файлы:
- file1.py (добавлена функция X)
- file2.vue (обновлен UI)

🧪 Проверено:
- pytest - OK
- npm run dev - OK
- curl /api/health - 200 OK

📝 Коммиты:
- abc1234: "Add feature X"

❌ Проблемы (если были):
- <что сломалось и как пофиксил>
```

---

## Команды для проверки

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
pytest -v
```

**Frontend:**
```bash
cd dashboard-vue
npm run dev
npm run test
```

**Bookmarklet:**
```bash
cd bookmarklet
npm run build
npm run watch
```

**API check:**
```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/docs  # Swagger UI
```

---

## Юмор приветствуется 🎭

Мы серьёзно относимся к качеству кода, но не к себе. Добрый сарказм и айтишные шутки делают работу веселее. Если что-то сломалось — можно пошутить, потом починить.

---

## Контакты с внешним миром

При необходимости:
- **YouGile API:** Для задач (ключ в settings.local.json)
- **GitHub:** PR через `gh pr create`
- **Railway:** Деплой автоматический при push в main

---

## Lab Server (192.168.1.74)

Домашний сервер с K3s для staging/dev окружений.

**SSH доступ:**
```bash
ssh -i ~/.ssh/id_ed25519 flomaster@192.168.1.74
```

**ОБЯЗАТЕЛЬНО:**
- **ПЕРЕД работой** — `lab start-errorlens`
- **ПОСЛЕ работы** — `lab stop-errorlens`

**Основные команды:**
```bash
lab start-errorlens   # Поднять ErrorLens + боты (~800MB RAM)
lab stop-errorlens    # Остановить
lab stop-all          # Остановить ВСЁ
lab status            # Проверить состояние
```

**K8s namespaces:**
- `errorlens-stage` — ErrorLens staging
- `bots` — Telegram боты

**Credentials:** см. `.secrets/lab-credentials.md` (не в git!)

**Полное руководство:** `docs/LAB_CONTROL_GUIDE.md`

---

*Последнее обновление: 2025-12-08 (Lab server docs added)*
