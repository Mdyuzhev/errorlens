# ErrorLens — Agent Context

> 🎯 Это главный файл контекста. Claude Code читает его автоматически при старте сессии.

## Кто мы

- **Claude Opus** = "шеф" — стратегические решения, архитектура, планирование
- **Claude Code** = "коллега" — реализация, код, тесты
- Референс: "Следствие ведут Колобки" 🔍

## Проект

**ErrorLens** — AI-powered QA platform. Bookmarklet записывает browser errors/requests, отправляет на backend с LLM анализом. Zero-friction: drag-n-drop установка, работает на любом сайте.

**Production:** https://errorlens-production.up.railway.app  
**Repo:** github.com/Mdyuzhev/errorlens (private)  
**Demo:** demo / ErrorLenseTest

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
├── main.py              # FastAPI entrypoint (~130 LOC, уже slim)
├── config.py            # Pydantic Settings
├── database.py          # SQLAlchemy async engine
│
├── models/              # SQLAlchemy ORM
│   ├── db_models.py     # Session, TestCase, Task, Article, Project...
│   └── user.py          # User model
│
├── routers/             # API endpoints (thin controllers)
│   ├── sessions.py      # ✅ Использует Service
│   ├── projects.py      # ✅ Использует Service
│   ├── auth.py          # ✅ OK
│   ├── articles.py      # ⚠️ Напрямую с моделями — нужен Service
│   ├── tasks.py         # ⚠️ Напрямую с моделями — нужен Service
│   ├── testcases.py     # ⚠️ Напрямую с моделями — нужен Service
│   └── ...
│
├── services/            # Business logic
│   ├── session_service.py
│   ├── project_service.py
│   ├── export_service.py
│   ├── auth.py
│   └── seed_demo.py
│
├── repositories/        # Data access (CRUD)
│   ├── base.py          # Generic CRUD
│   ├── session_repo.py
│   ├── project_repo.py
│   ├── testcase_repo.py
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

**ВНИМАНИЕ: Сейчас дублирование!**

```
bookmarklet/
├── recorder.js          # 2438 LOC — LEGACY МОНОЛИТ (используется в prod!)
├── recorder.min.js      # Minified legacy
│
└── src/                 # НОВАЯ модульная структура (НЕ используется!)
    ├── index.js         # Entry point
    ├── core/            # config, state, api
    ├── interceptors/    # console, fetch, xhr, errors
    ├── ui/              # widget, styles
    └── utils/           # helpers
```

**Задача WAVE 3.2:** Настроить esbuild, собрать src/ → dist/, заменить legacy.

---

## Текущий Wave

**WAVE 3.2: Code Refactoring**

Цель: закрыть техдолг, сделать код правильным.

Фазы:
1. **Bookmarklet** — модуляризация, удаление legacy
2. **Backend** — добавить недостающие Services
3. **Frontend** — split крупных компонентов (>500 LOC)
4. **Tests & Docs** — покрытие новых сервисов

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
| Backend refactoring | `docs/TECHNICAL_AUDIT_2025-12-05.md` |
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

*Последнее обновление: 2025-12-05*
