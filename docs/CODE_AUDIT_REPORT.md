# ErrorLens Code Audit Report

**Date:** 2025-12-05
**Branch:** feature/wave-3
**Commit:** f6d376f

---

## Executive Summary

### Критичные проблемы

| Файл | Строк | Проблема |
|------|-------|----------|
| `bookmarklet/recorder.js` | 2438 | **МОНОЛИТ** - 120 функций, 47 event listeners, нужен split |
| `backend/app/main.py` | 830 | Много кода в одном файле, смешаны роуты и конфиг |
| `dashboard-vue/src/views/DashboardView.vue` | 687 | Большой компонент, можно разбить |
| `backend/app/routers/sessions.py` | 530 | Бизнес-логика в роутере вместо service |
| `dashboard-vue/src/views/ResultsView.vue` | 521 | Большой компонент |
| `dashboard-vue/src/views/TestCasesView.vue` | 500 | На грани допустимого |

### Code Quality Score

| Метрика | Значение | Норма | Статус |
|---------|----------|-------|--------|
| Max file size (LOC) | 2438 | <500 | FAIL |
| Files >500 LOC | 6 | 0 | FAIL |
| Repository layer | 0 files | Required | FAIL |
| Service layer usage | 0% | 100% | FAIL |
| Hardcoded URLs | 3 | 0 | WARN |
| TODOs/FIXMEs | 0 | - | OK |

---

## Детальный анализ

### 1. Файлы по размеру (топ-20)

```
  2438 ./bookmarklet/recorder.js          ❌ CRITICAL
   830 ./backend/app/main.py              ⚠️ WARNING
   687 ./dashboard-vue/src/views/DashboardView.vue  ⚠️ WARNING
   530 ./backend/app/routers/sessions.py  ⚠️ WARNING
   521 ./dashboard-vue/src/views/ResultsView.vue    ⚠️ WARNING
   500 ./dashboard-vue/src/views/TestCasesView.vue  ⚠️ BORDERLINE
   495 ./dashboard-vue/src/views/ArticlesView.vue   ✓ OK
   470 ./backend/app/ticket_generator.py  ✓ OK
   448 ./dashboard-vue/src/views/TasksView.vue      ✓ OK
   447 ./dashboard-vue/src/views/SettingsView.vue   ✓ OK
   409 ./backend/app/generators/testit.py ✓ OK
   407 ./dashboard-vue/src/components/RecorderWidget.vue ✓ OK
   394 ./backend/app/generators/pytest.py ✓ OK
   372 ./backend/app/models_pydantic.py   ✓ OK
   356 ./backend/app/services/seed_demo.py ✓ OK
   349 ./backend/app/models/db_models.py  ✓ OK
```

### 2. Архитектурные проблемы

#### 2.1 Отсутствует Repository Layer

```
backend/app/
├── routers/        ✓ 7 files (Controllers)
├── services/       ⚠️ 3 files (недостаточно)
├── repositories/   ❌ НЕ СУЩЕСТВУЕТ!
├── generators/     ✓ 9 files
└── models/         ✓ 3 files
```

**Проблема:** Все роутеры напрямую работают с SQLAlchemy моделями, минуя service и repository layers.

**Файлы с нарушением:**
- `backend/app/routers/articles.py` - direct model import
- `backend/app/routers/auth.py` - direct model import
- `backend/app/routers/sessions.py` - direct model import
- `backend/app/routers/tasks.py` - direct model import
- `backend/app/routers/testcases.py` - direct model import
- `backend/app/routers/testruns.py` - direct model import

#### 2.2 Hardcoded Values

```python
# backend/app/generators/base.py:23
return "http://localhost"

# backend/app/generators/cypress.py:185-189
"baseUrl": "http://localhost:3000",
"API_URL": "http://localhost:8000"
```

### 3. Bookmarklet Analysis (recorder.js)

#### Статистика
- **Строк кода:** 2438
- **Функций:** 120
- **Event listeners:** 47
- **Глобальных переменных:** ~30

#### Функции по категориям

**Interceptors (перехватчики):**
```
- interceptConsole()
- restoreConsole()
- setupErrorHandler()
- restoreErrorHandler()
- setupRejectionHandler()
- restoreRejectionHandler()
- interceptFetch()
- restoreFetch()
- interceptXHR()
- restoreXHR()
```

**UI (интерфейс):**
```
- createWidget()
- createTopBarWidget()
- createClassicWidget()
- makeWidgetDraggable()
- showOnboarding()
- showModeMenu()
- showModeMenuForPill()
- showModal()
- showResult()
- showErrorWithRetry()
- updateEventCounter()
- updateBarToRecording()
- updateBarToDone()
- updateBarToIdle()
- removeWidget()
```

**Utils (утилиты):**
```
- isJunkUrl()
- detectApiBaseUrl()
- normalizeApiUrl()
- getTimestamp()
- getStackTrace()
- isErrorStatus()
- headersToObject()
- loadHtml2Canvas()
```

**Core (ядро):**
```
- init()
- startRecording()
- handleRecordClick()
- handleWidgetClick()
```

### 4. Frontend Components

| Component | LOC | Complexity | Refactor? |
|-----------|-----|------------|-----------|
| DashboardView.vue | 687 | High | Yes - split sessions/stats |
| ResultsView.vue | 521 | Medium | Maybe |
| TestCasesView.vue | 500 | Medium | Maybe |
| ArticlesView.vue | 495 | Medium | OK |
| TasksView.vue | 448 | Medium | OK |
| SettingsView.vue | 447 | Low | OK |

---

## Рекомендации для WAVE_3.2

### Приоритет 1: Критично (P1)

1. **[ ] Разбить `recorder.js` на модули**
   - Оценка: 4-6 часов
   - Результат: 5-7 файлов по ~300-500 строк

2. **[ ] Добавить Repository layer**
   - Оценка: 3-4 часа
   - Результат: Чистая архитектура, тестируемость

3. **[ ] Вынести бизнес-логику из роутеров в services**
   - Оценка: 3-4 часа
   - Результат: Thin controllers, fat services

### Приоритет 2: Важно (P2)

4. **[ ] Разбить main.py**
   - Оценка: 1-2 часа
   - Вынести: конфиг, middleware setup, static files

5. **[ ] Вынести hardcoded URLs в config**
   - Оценка: 30 мин
   - Файлы: generators/base.py, generators/cypress.py

6. **[ ] Разбить DashboardView.vue**
   - Оценка: 2-3 часа
   - На: SessionsPanel, StatsPanel, FilterPanel

### Приоритет 3: Желательно (P3)

7. **[ ] Добавить type hints везде**
   - Оценка: 2-3 часа

8. **[ ] Унифицировать error handling**
   - Оценка: 1-2 часа

9. **[ ] Добавить больше docstrings**
   - Оценка: 1-2 часа

---

## План рефакторинга WAVE_3.2

### A. Bookmarklet модуляризация

**Текущая структура:**
```
bookmarklet/
└── recorder.js (2438 LOC) ❌
```

**Целевая структура:**
```
bookmarklet/
├── index.js              # Entry point (IIFE wrapper) ~50 LOC
├── src/
│   ├── interceptors/
│   │   ├── console.js    # Console interception ~100 LOC
│   │   ├── fetch.js      # Fetch interception ~150 LOC
│   │   ├── xhr.js        # XHR interception ~150 LOC
│   │   └── errors.js     # Error handlers ~80 LOC
│   ├── ui/
│   │   ├── widget.js     # Main widget ~200 LOC
│   │   ├── modal.js      # Results modal ~150 LOC
│   │   ├── onboarding.js # Onboarding UI ~100 LOC
│   │   └── styles.js     # CSS-in-JS ~200 LOC
│   ├── core/
│   │   ├── state.js      # Session state ~50 LOC
│   │   ├── storage.js    # localStorage ~50 LOC
│   │   ├── api.js        # Backend API ~100 LOC
│   │   └── config.js     # Configuration ~50 LOC
│   └── utils/
│       ├── dom.js        # DOM helpers ~50 LOC
│       ├── url.js        # URL utils ~80 LOC
│       └── format.js     # Formatters ~50 LOC
├── build.js              # Rollup/esbuild bundle script
└── recorder.min.js       # Bundled output
```

### B. Backend реструктуризация

**Текущая структура:**
```
backend/app/
├── routers/          # ❌ Содержит бизнес-логику
├── services/         # ⚠️ Недоиспользуется
├── models/           # ✓ OK
└── main.py           # ❌ 830 LOC монолит
```

**Целевая структура:**
```
backend/app/
├── api/
│   └── v1/
│       ├── routers/      # Thin controllers only
│       │   ├── sessions.py
│       │   ├── testcases.py
│       │   └── ...
│       └── deps.py       # FastAPI dependencies
├── core/
│   ├── config.py         # Settings (from main.py)
│   ├── security.py       # Auth helpers
│   └── exceptions.py     # Custom exceptions
├── services/             # Business logic
│   ├── session_service.py
│   ├── analysis_service.py
│   ├── export_service.py
│   └── testcase_service.py
├── repositories/         # NEW! Data access
│   ├── base.py           # Generic CRUD
│   ├── session_repo.py
│   ├── user_repo.py
│   └── testcase_repo.py
├── models/               # SQLAlchemy models (unchanged)
├── schemas/              # Pydantic schemas (from models_pydantic.py)
└── main.py               # Slim entry point ~100 LOC
```

### C. Frontend улучшения

**DashboardView.vue (687 LOC) → Split:**
```
dashboard-vue/src/
├── views/
│   └── DashboardView.vue      # Container ~100 LOC
└── components/
    └── dashboard/
        ├── SessionsList.vue   # Sessions table ~200 LOC
        ├── SessionDetail.vue  # Session modal ~200 LOC
        ├── StatsPanel.vue     # Statistics ~100 LOC
        └── FiltersPanel.vue   # Search/filters ~80 LOC
```

---

## Оценка трудозатрат

| Задача | Часы | Приоритет | Сложность |
|--------|------|-----------|-----------|
| Bookmarklet split | 4-6h | P1 | High |
| Repository layer | 3-4h | P1 | Medium |
| Services refactor | 3-4h | P1 | Medium |
| main.py split | 1-2h | P2 | Low |
| Config extraction | 0.5h | P2 | Low |
| DashboardView split | 2-3h | P2 | Medium |
| Type hints | 2-3h | P3 | Low |
| Error handling | 1-2h | P3 | Low |
| Docstrings | 1-2h | P3 | Low |
| **Итого P1** | **10-14h** | | |
| **Итого P1+P2** | **14-20h** | | |
| **Итого все** | **18-27h** | | |

---

## Заключение

Кодовая база ErrorLens находится в **работоспособном, но неоптимальном** состоянии:

### Положительное
- Нет TODO/FIXME в коде
- Хорошая структура generators
- Работающие интеграции (TestIT, LLM providers)
- Покрытие тестами базовых сценариев

### Требует внимания
- **recorder.js** - критический монолит, главный кандидат на рефакторинг
- Архитектура бэкенда - отсутствует разделение слоёв
- Некоторые Vue компоненты переросли оптимальный размер

### Рекомендация

Выполнить рефакторинг в **WAVE_3.2** с фокусом на:
1. Модуляризацию bookmarklet (максимальный эффект)
2. Добавление Repository layer (улучшит тестируемость)
3. Перенос логики из routers в services (clean architecture)

**Ожидаемый результат:** Более поддерживаемый, тестируемый и расширяемый код.

---

*Report generated automatically during WAVE_3.1 audit*
